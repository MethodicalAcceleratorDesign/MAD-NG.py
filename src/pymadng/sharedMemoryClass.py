import numpy as np  # For arrays  (Works well with multiprocessing and mmap)
from resource import getpagesize  # To get page size
from multiprocessing import shared_memory  # For shared memory
from typing import Any # To make stuff look nicer

class shmBuffer:
    __PAGE_SIZE = getpagesize()  # To allow to work on multiple different machines
    start = 0   # bytes
    end = 0     # bytes
    # readWriteLock = 0

    def __init__(self, ram_limit: int) -> None:
        self.file = shared_memory.SharedMemory(create=True, size=ram_limit)
        self.name = self.file.name
        self.__bufferInfo = np.memmap(            
            "/dev/shm/" + self.name,
            dtype=np.int32,
            mode="w+",
            shape=(3,),
        )
        self.capacity = int(ram_limit - self.__PAGE_SIZE)  # bytes
        self.__numpyBuffer = np.memmap(
            "/dev/shm/" + self.name,
            dtype=np.byte,
            mode="w+",
            shape=self.capacity,
            offset=self.__PAGE_SIZE
        )
        self.__setProperties(self.start, self.end)

    def __setProperties(self, start: int, end: int) -> None:
        self.start = start
        self.end = end
        self.__bufferInfo[:] = np.array([self.start, self.end, self.capacity], dtype=np.int32)[:]
        self.__bufferInfo.flush()

    def __getProperties(self):
        self.__bufferInfo.flush()
        self.start = self.__bufferInfo[0]
        self.end = self.__bufferInfo[1]

    def write(self, data: np.ndarray) -> None:
        """Enter a numpy array which will be entered into shared memory, if not send to MAD process, synchronisation problems will occur"""
        self.__getProperties()
        dataLen = min(self.capacity - self.end, data.nbytes)
        # Change below to be bit manipulation
        bufWrittenLocation = (self.end + data.nbytes) % (self.capacity)
        if (  # Simplify - store stuff to prevent this
            self.end > self.start
            and bufWrittenLocation < self.end
            and bufWrittenLocation >= self.start
        ) or (
            self.end < self.start
            and not bufWrittenLocation > self.end
            and not bufWrittenLocation < self.start
        ):
            raise (
                MemoryError(
                    "Shared memory available to send to MAD full, read from MAD to continue"
                )
            )
        self.__numpyBuffer[self.end : self.end + dataLen] = np.frombuffer(
            data.tobytes(), dtype=np.byte
        )[:dataLen]
        if dataLen < data.nbytes: #Seperate the whole buffer from writeable buffer!
            self.__numpyBuffer[0 : data.nbytes - dataLen] = np.frombuffer(
                data.tobytes(), dtype=np.byte
            )[dataLen:]
        self.__numpyBuffer.flush()
        self.__setProperties(
            self.start,
            (np.intc(bufWrittenLocation)// self.__PAGE_SIZE + 1) * self.__PAGE_SIZE,
        )

    def read(self, dataSize: int) -> Any:
        """Enter datasize in bytes to read the data"""
        self.__getProperties()
        dataLen = min(self.capacity - self.start, dataSize)
        # Change below to be bit manipulation
        newReadLocation = (((self.start + dataSize) % (self.capacity))// self.__PAGE_SIZE + 1) * self.__PAGE_SIZE
        assert newReadLocation == (((self.start + dataSize)// self.__PAGE_SIZE + 1) * self.__PAGE_SIZE) % (self.capacity), "Houston, we have a problem"
        returnData = self.__numpyBuffer[
            self.start : self.start + dataLen
        ]  # Likely will have a problem
        if dataLen < dataSize:
            returnData = np.concatenate(
                (returnData, self.__numpyBuffer[0: dataSize - dataLen])
            )
        # Need to set before or after? After means errors with data does not affect shared memory:
        self.__setProperties(np.intc(newReadLocation), self.end)
        self.__numpyBuffer.flush()
        return returnData

    def close(self):
        self.__numpyBuffer = None
        self.file.close()  # Closes the shared memory, needs to be done before unlinked
        self.file.unlink()  # Deletes the shared memory (prevents memory leaks)

    def __del__(self):
        self.__numpyBuffer = None
        del self.file