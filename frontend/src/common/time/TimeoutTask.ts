export class TimeoutTask implements TimeTask {
    cancelled = false;
  
    constructor(
      public nextTime: number,
      private cb: (now: number) => void
    ) {}
  
    run(now: number) {
      this.cb(now);
      this.cancelled = true;
    }
  }
  