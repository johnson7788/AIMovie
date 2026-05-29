export class IntervalTask implements TimeTask {
    cancelled = false;
    count = 0;
  
    constructor(
      public interval: number,
      public nextTime: number,
      private cb: (count: number, now: number) => void
    ) {}
  
    run(now: number) {
      // 处理跳帧（后台 / tab 冻结）
      const n = Math.floor((now - this.nextTime) / this.interval) + 1;
      this.count += n;
      this.nextTime += n * this.interval;
  
      this.cb(this.count, now);
    }
  }