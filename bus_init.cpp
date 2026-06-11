#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include "pip.h"

// This creates the shared memory region that all nodes will access
CognitiveBus* init_bus() {
    int fd = shm_open("/aura_cognitive_bus", O_RDWR | O_CREAT, 0666);
    ftruncate(fd, sizeof(CognitiveBus));
    
    // Memory map the bus into this process's address space
    CognitiveBus* bus = (CognitiveBus*)mmap(NULL, sizeof(CognitiveBus), 
                                           PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    return bus;
}

