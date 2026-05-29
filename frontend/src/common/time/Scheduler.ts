import { MinHeap } from './MinHeap';
import { TimeoutTask } from './TimeoutTask';
import { IntervalTask } from './IntervalTask';
export class Scheduler {
    private heap = new MinHeap<TimeTask>(
      (a, b) => a.nextTime - b.nextTime
    );
    private ticking = false;
  
    constructor(private now: () => number) {}
  
    /* ========== Timeout ========== */
  
    setTimeout(cb: (now: number) => void, delay: number) {
      const task = new TimeoutTask(this.now() + delay, cb);
      this.heap.push(task);
      this.ensureTicking();
      return task;
    }
  
    clearTimeout(task: TimeTask) {
      task.cancelled = true;
    }
  
    /* ========== Interval ========== */
  
    setInterval(
      cb: (count: number, now: number) => void,
      interval: number
    ) {
      const task = new IntervalTask(
        interval,
        this.now() + interval,
        cb
      );
      this.heap.push(task);
      this.ensureTicking();
      return task;
    }
  
    clearInterval(task: TimeTask) {
      task.cancelled = true;
    }
  
    /* ========== 调度循环 ========== */
  
    private ensureTicking() {
      if (!this.ticking) this.tick();
    }
  
    private tick = () => {
      this.ticking = true;
      const now = this.now();
  
      while (this.heap.size && this.heap.peek()!.nextTime <= now) {
        const task = this.heap.pop()!;
        if (task.cancelled) continue;
  
        task.run(now);
  
        // interval 会重新入堆，timeout 不会
        if (!task.cancelled) {
          this.heap.push(task);
        }
      }
  
      if (this.heap.size) {
        requestAnimationFrame(this.tick);
      } else {
        this.ticking = false;
      }
    };
  }
  