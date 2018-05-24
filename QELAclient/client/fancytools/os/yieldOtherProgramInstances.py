
import psutil  
import sys
import os


def yieldOtherProgramInstances():
    '''
    yields all other processed of the same executable
    '''
    this_prog_name = os.path.basename(sys.executable)
    pid = os.getpid()
    for p in psutil.process_iter():
        if p.name() == this_prog_name and p.pid != pid:
            yield p
  

if __name__ == '__main__':
    from time import sleep
    
    print(list(yieldOtherProgramInstances()))
    sleep(10)
