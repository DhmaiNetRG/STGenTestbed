
"""
CoAP protocol plugin for STGen – active mode with multi-client support.
FIXED: Creates multiple client contexts for fair comparison with MQTT.
"""

import sys
import asyncio
import json
import logging
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from aiocoap import Context, Message, Code, resource
except ImportError as exc:
    raise ImportError(
        "aiocoap not installed – run:  pip install aiocoap[all]==0.4.7"
    ) from exc

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from stgen.protocol_interface import ProtocolInterface

_LOG = logging.getLogger("coap")


# --------------------------------------------------------------------------- #
class SimpleResource(resource.Resource):
    """A basic CoAP resource that handles PUT requests with logging."""

    async def render_put(self, request):
        try:
            payload_str = request.payload.decode()
            data = json.loads(payload_str)
            _LOG.info("SERVER RECEIVED: %s", json.dumps(data, indent=2))
        except Exception as e:
            _LOG.warning("Failed to parse received data: %s", e)
            _LOG.debug("Raw payload: %s", request.payload)
        
        return Message(code=Code.CHANGED, payload=b"OK")


# --------------------------------------------------------------------------- #
class Protocol(ProtocolInterface):
    """CoAP plug-in that satisfies STGen ProtocolInterface."""

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg)
        
        # Server context
        self._server_ctx: Context | None = None
        self._server_thread: threading.Thread | None = None
        self._server_loop: asyncio.AbstractEventLoop | None = None
        
        # Client contexts (FIXED: Now we actually create these!)
        self._client_contexts: List[Context] = []
        self._client_loop: asyncio.AbstractEventLoop | None = None
        self._client_thread: threading.Thread | None = None
        self._client_ready = threading.Event()
        
        self._lat: List[float] = []
        self._alive: bool = True
        self._msg_count: int = 0

    # ---------- life-cycle -------------------------------------------------- #
    def start_server(self) -> None:
        """Start aiocoap server in a dedicated thread."""
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        time.sleep(0.5)  # give the socket time to bind
        _LOG.info("CoAP server thread started")

    def start_clients(self, num: int) -> None:
        """
        FIXED: Create multiple CoAP client contexts.
        This matches MQTT's architecture for fair comparison.
        """
        _LOG.info("CoAP: Creating %d client contexts...", num)
        
        # Start client event loop in separate thread
        self._client_thread = threading.Thread(
            target=self._run_client_loop, 
            args=(num,),
            daemon=True
        )
        self._client_thread.start()
        
        # Wait for clients to be ready
        if not self._client_ready.wait(timeout=5.0):
            raise RuntimeError("Client contexts failed to initialize")
        
        _LOG.info("CoAP: %d client contexts ready", len(self._client_contexts))

    def stop(self) -> None:
        """Stop server and all client contexts."""
        self._alive = False
        
        # Stop server
        if self._server_loop and self._server_ctx:
            fut = asyncio.run_coroutine_threadsafe(
                self._server_ctx.shutdown(), 
                self._server_loop
            )
            try:
                fut.result(2)
            except (Exception, AttributeError) as e:
                # Suppress known aiocoap race condition during shutdown
                if "'NoneType' object has no attribute 'values'" not in str(e):
                    _LOG.warning("Server shutdown error: %s", e)
        
        # Stop clients
        if self._client_loop:
            # Shutdown all client contexts
            for ctx in self._client_contexts:
                try:
                    fut = asyncio.run_coroutine_threadsafe(
                        ctx.shutdown(),
                        self._client_loop
                    )
                    fut.result(1)
                except (Exception, AttributeError) as e:
                    # Suppress known aiocoap race condition
                    if "'NoneType' object has no attribute 'values'" not in str(e):
                        _LOG.warning("Client shutdown error: %s", e)
            
            # Stop loop
            try:
                self._client_loop.call_soon_threadsafe(self._client_loop.stop)
            except:
                pass
        
        # Join threads
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2)
        if self._client_thread and self._client_thread.is_alive():
            self._client_thread.join(timeout=2)
        
        _LOG.info("CoAP server stopped. Messages sent: %d", self._msg_count)

    # ---------- active-mode send ------------------------------------------- #
    def send_data(self, client_id: str, data: Dict) -> Tuple[bool, float]:
        """
        Thread-safe CoAP PUT + RTT measurement.
        FIXED: Now selects specific client context (like MQTT does).
        """
        if not self._client_loop or not self._client_contexts:
            _LOG.error("CoAP client contexts not ready")
            return False, 0.0
        
        # FIXED: Select client context based on client_id (like MQTT)
        try:
            idx = int(client_id.split("_")[-1])
            ctx = self._client_contexts[idx % len(self._client_contexts)]
        except (ValueError, IndexError):
            ctx = self._client_contexts[0]
        
        self._msg_count += 1
        _LOG.info("CLIENT [%s] SENDING (msg #%d): %s", 
                  client_id, self._msg_count, json.dumps(data, indent=2))
        
        # Submit to client event loop
        future = asyncio.run_coroutine_threadsafe(
            self._send_async(data, ctx), 
            self._client_loop
        )
        
        try:
            return future.result(timeout=30.0)  # 30s timeout (longer for network-impaired tests)
        except asyncio.TimeoutError:
            _LOG.warning("Send timeout for %s (network impaired?)", client_id)
            return False, 0.0
        except Exception as e:
            _LOG.error("Send error: %s", e)
            return False, 0.0

    # ---------- internal async --------------------------------------------- #
    def _build_site(self):
        """Build CoAP resource tree."""
        root = resource.Site()

        class RootResource(resource.Resource):
            async def render_put(self, request):
                try:
                    payload_str = request.payload.decode()
                    data = json.loads(payload_str)
                    _LOG.info(" SERVER RECEIVED (root): %s", json.dumps(data, indent=2))
                except Exception as e:
                    _LOG.warning("Failed to parse received data: %s", e)
                return Message(code=Code.CHANGED, payload=b"OK")

        root.add_resource([], RootResource())
        root.add_resource(['data'], SimpleResource())
        return root

    def _run_server(self) -> None:
        """Run aiocoap server event loop (in separate thread)."""
        asyncio.set_event_loop(asyncio.new_event_loop())
        self._server_loop = asyncio.get_event_loop()
        try:
            self._server_ctx = self._server_loop.run_until_complete(
                Context.create_server_context(
                    self._build_site(),
                    bind=(self.cfg["server_ip"], self.cfg["server_port"]),
                )
            )
            _LOG.info(
                "CoAP server listening on %s:%s",
                self.cfg["server_ip"],
                self.cfg["server_port"],
            )
            self._server_loop.run_forever()
        finally:
            if self._server_ctx:
                self._server_loop.run_until_complete(self._server_ctx.shutdown())

    def _run_client_loop(self, num_clients: int) -> None:
        """
        FIXED: Create and manage multiple client contexts.
        Runs in separate thread with its own event loop.
        """
        asyncio.set_event_loop(asyncio.new_event_loop())
        self._client_loop = asyncio.get_event_loop()
        
        try:
            # Create all client contexts
            for i in range(num_clients):
                ctx = self._client_loop.run_until_complete(
                    Context.create_client_context()
                )
                self._client_contexts.append(ctx)
                _LOG.debug("Created client context %d", i)
            
            # Signal that clients are ready
            self._client_ready.set()
            
            # Run event loop to handle requests
            self._client_loop.run_forever()
            
        except Exception as e:
            _LOG.error("Client loop error: %s", e)
            self._client_ready.set()  # Unblock even on error
        finally:
            # Cleanup
            for ctx in self._client_contexts:
                try:
                    self._client_loop.run_until_complete(ctx.shutdown())
                except:
                    pass

    async def _send_async(self, data: Dict, ctx: Context) -> Tuple[bool, float]:
        """
        Perform a CoAP PUT request and measure RTT.
        FIXED: Now takes specific context as parameter.
        """
        uri = f'coap://{self.cfg["server_ip"]}:{self.cfg["server_port"]}/data'
        t0 = time.perf_counter()
        
        try:
            req = Message(
                code=Code.PUT,
                uri=uri,
                payload=json.dumps(data).encode(),
                content_format=0,
            )
            
            # Use the specific context passed in
            resp = await ctx.request(req).response
            
            latency_ms = (time.perf_counter() - t0) * 1000
            self._lat.append(latency_ms)
            
            _LOG.info(" CLIENT RECEIVED RESPONSE: code=%s, RTT=%.2fms", 
                     resp.code, latency_ms)
            return True, time.perf_counter()
            
        except Exception as e:
            _LOG.error(" CLIENT REQUEST FAILED: %s", e)
            return False, 0.0

    def is_alive(self) -> bool:
        """Check if CoAP clients are still alive."""
        return self._alive


__all__ = ["Protocol"]