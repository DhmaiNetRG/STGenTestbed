#pragma once
#include <stdint.h>
#include <time.h>
typedef struct __attribute__((packed)) {
    uint32_t seq;
    uint64_t send_time_us;
    char payload[];
} stgen_hdr_t;
static inline uint64_t now_us(){
    struct timespec ts; clock_gettime(CLOCK_REALTIME, &ts);
    return ts.tv_sec*1000000 + ts.tv_nsec/1000;
}