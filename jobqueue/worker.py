import os, sys
import logging
import traceback
import time
import thread
from multiprocessing import Process

from jobqueue import runjob, store
from jobqueue.client import connect

store.ROOT = '/tmp/worker/%s'
DEFAULT_DISPATCHER = 'http://reflectometry.org:5000'
POLLRATE = 60

def wait_for_result(remote, id, process):
    """
    Wait for job processing to finish.  Meanwhile, prefetch the next
    request.
    """
    next_request = { 'request': None }
    cancelling = False
    while True:
        print "joining process"
        process.join(POLLRATE)
        print "joined or timed out"
        if not process.is_alive(): break
        ret = remote.status(id)
        if ret.status == 'CANCEL':
            print "cancelling process"
            process.terminate()
            cancelling = True
            break
        if not next_request['request']:
            next_request = remote.nextjob(queue=queue)

    try:
        result = runjob.results(id)
    except KeyError:
        if cancelling:
            result = { 'status': 'CANCEL' }
        else:
            result = { 'status': 'ERROR' }

    return result, next_request

def update_remote(remote, id, queue, result):
    print "updating remote"
    print "step"
    path= store.path(id)
    files = [os.path.join(path,f) for f in os.listdir(path)]
    remote.putfiles(id, files, queue)
    print "step"
    remote.postjob(id, result, queue)
    print "done"

def serve(dispatcher, queue):
    assert queue is not None
    next_request = { 'request': None }
    remote = connect(dispatcher)
    while True:
        if not next_request['request']:
            try:
                next_request = remote.nextjob(queue=queue)
            except:
                logging.error(traceback.format_exc())
                next_request = {'request': None}
        if next_request['request']:
            jobid = next_request['id']
            assert jobid != None
            store.create(jobid)
            process = Process(target=runjob.run, 
                              args=(jobid,next_request['request']))
            process.start()
            result, next_request = wait_for_result(remote, jobid, process)
            thread.start_new_thread(update_remote, 
                                    (remote, jobid, queue, result))
        else:
            time.sleep(POLLRATE)

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print "Requires queue name"
    queue = sys.argv[1]
    dispatcher = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DISPATCHER
    serve(queue=queue, dispatcher=dispatcher)
