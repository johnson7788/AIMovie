export class MinHeap<T> {
    private data: T[] = [];
  
    constructor(private compare: (a: T, b: T) => number) {}
  
    peek(): T | undefined {
      return this.data[0];
    }
  
    push(item: T) {
      this.data.push(item);
      this.bubbleUp(this.data.length - 1);
    }
  
    pop(): T | undefined {
      if (this.data.length === 1) return this.data.pop();
      const top = this.data[0];
      this.data[0] = this.data.pop()!;
      this.bubbleDown(0);
      return top;
    }
  
    get size() {
      return this.data.length;
    }
  
    private bubbleUp(i: number) {
      while (i > 0) {
        const p = (i - 1) >> 1;
        if (this.compare(this.data[i], this.data[p]) >= 0) break;
        [this.data[i], this.data[p]] = [this.data[p], this.data[i]];
        i = p;
      }
    }
  
    private bubbleDown(i: number) {
      const n = this.data.length;
      while (true) {
        let s = i;
        const l = i * 2 + 1;
        const r = l + 1;
  
        if (l < n && this.compare(this.data[l], this.data[s]) < 0) s = l;
        if (r < n && this.compare(this.data[r], this.data[s]) < 0) s = r;
        if (s === i) break;
  
        [this.data[i], this.data[s]] = [this.data[s], this.data[i]];
        i = s;
      }
    }
  }
  