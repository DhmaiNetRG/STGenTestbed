#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <signal.h>
#include "stgen_compat.h"

int run = 1;
void handle_sig(int s) { run = 0; }

int main(int argc, char *argv[]) {
    if (argc < 4) { // exe ip port client_id
        fprintf(stderr, "Usage: %s <ip> <port> <id>\n", argv[0]);
        return 1;
    }

    const char* ip = argv[1];
    int port = atoi(argv[2]);
    // argv[3] is id, maybe use in payload if needed
    // argv[4] (optional) is the generation rate in Hz; default 10 Hz.
    double rate_hz = (argc >= 5) ? atof(argv[4]) : 10.0;
    if (rate_hz <= 0.0) rate_hz = 10.0;
    useconds_t period_us = (useconds_t)(1000000.0 / rate_hz);

    int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in servaddr;
    
    memset(&servaddr, 0, sizeof(servaddr));
    servaddr.sin_family = AF_INET;
    servaddr.sin_port = htons(port);
    servaddr.sin_addr.s_addr = inet_addr(ip);
    
    signal(SIGTERM, handle_sig);
    signal(SIGINT, handle_sig);
    
    stgen_hdr_t *hdr = malloc(sizeof(stgen_hdr_t) + 100); // 100 byte payload
    hdr->seq = 0;
    
    while(run) {
        hdr->seq++;
        hdr->send_time_us = now_us();
        
        sendto(sockfd, hdr, sizeof(stgen_hdr_t) + 100, 0, (const struct sockaddr *)&servaddr, sizeof(servaddr));

        usleep(period_us); // generation period derived from rate_hz (argv[4], default 10 Hz)
    }
    
    free(hdr);
    close(sockfd);
    return 0;
}
