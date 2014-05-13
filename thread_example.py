import time
from rjgtoys.progressive.thread import Thread

@Thread()
def do_work(pt,interval,count):
    pt.set_goal(count)
    for i in range(0,count):
        if pt.stopping():
            return

        time.sleep(interval)
        pt.update(1)
#        print "worker has done %d" % (i)



do_work(1,2)

do_work.start(1,20)

while True:
    do_work.sample()
    eta = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(do_work.eta))
    print "%d/%d in %ds %d%% %s %d" % (do_work.done,do_work.steps,do_work.elapsed,do_work.pcdone,eta,do_work.ttg)
    if do_work.pcdone == 100:
        break
    time.sleep(0.5)
#    print "Working",s.started()
    
do_work.wait()
