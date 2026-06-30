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
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }

    int port = atoi(argv[2]);
    int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in servaddr, cliaddr;
    socklen_t len;
    
    memset(&servaddr, 0, sizeof(servaddr));
    servaddr.sin_family = AF_INET;
    servaddr.sin_addr.s_addr = inet_addr(argv[1]); // Bind IP
    servaddr.sin_port = htons(port);
    
    if (bind(sockfd, (const struct sockaddr *)&servaddr, sizeof(servaddr)) < 0) {
        perror("bind failed");
        return 1;
    }
    
    FILE *fp = fopen("recv.log", "w");
    if (!fp) {
        perror("recv.log");
        return 1;
    }
    setlinebuf(fp); // Ensure lines are written
    
    signal(SIGTERM, handle_sig);
    signal(SIGINT, handle_sig);
    
    uint8_t buffer[1024];
    while(run) {
        len = sizeof(cliaddr);
        int n = recvfrom(sockfd, buffer, sizeof(buffer), 0, (struct sockaddr *)&cliaddr, &len);
        if (n >= sizeof(stgen_hdr_t)) {
            uint64_t now = now_us();
            stgen_hdr_t *hdr = (stgen_hdr_t*)buffer;
            
            int64_t lat = now - hdr->send_time_us;
            if (lat < 0) lat = 0; // clock skew?
            
            fprintf(fp, "%u %ld\n", hdr->seq, lat);
        }
    }
    
    fclose(fp);
    close(sockfd);
    return 0;
}
