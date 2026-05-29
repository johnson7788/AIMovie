// dispatcher.ts
export interface EventCallback {
    fn: (data?: any) => void;
    context?: any;
}
export interface EventHandler {
    (event: string, data?: any): void;
}
export class CallbackRegistry {
    private _callbacks: Record<string, EventCallback[]> = {};
  
    get(name: string) {
      return this._callbacks[prefix(name)];
    }
  
    add(name: string, callback: (data?: any) => void, context?: any) {
      const prefixed = prefix(name);
      this._callbacks[prefixed] = this._callbacks[prefixed] || [];
      this._callbacks[prefixed].push({ fn: callback, context });
    }
  
    remove(name?: string, callback?: Function, context?: any) {
      if (!name && !callback && !context) {
        this._callbacks = {};
        return;
      }
      const names = name ? [prefix(name)] : Object.keys(this._callbacks);
      if (callback || context) {
        this.removeCallback(names, callback, context);
      } else {
        this.removeAllCallbacks(names);
      }
    }
  
    private removeCallback(names: string[], callback?: Function, context?: any) {
      names.forEach(name => {
        this._callbacks[name] = (this._callbacks[name] || []).filter(
          oning =>
            (callback && callback !== oning.fn) ||
            (context && context !== oning.context)
        );
        if (this._callbacks[name].length === 0) {
          delete this._callbacks[name];
        }
      });
    }
  
    private removeAllCallbacks(names: string[]) {
      names.forEach(name => {
        delete this._callbacks[name];
      });
    }
  }
  
  export class Dispatcher {
    private callbacks = new CallbackRegistry();
    private globalCallbacks: EventHandler[] = [];
    constructor(private failThrough?: EventHandler) {}
  
    on(event: string, callback: (data?: any) => void, context?: any) {
      this.callbacks.add(event, callback, context);
      return this;
    }
  
    onGlobal(callback: EventHandler) {
      this.globalCallbacks.push(callback);
      return this;
    }
  
    off(event?: string, callback?: Function, context?: any) {
      this.callbacks.remove(event, callback, context);
      return this;
    }
  
    emit(event: string, data?: any) {
      this.globalCallbacks.forEach(cb => cb(event, data));
      const cbs = this.callbacks.get(event);
      if (cbs?.length) {
        cbs.forEach(c => c.fn.call(c.context || window, data));
      } else if (this.failThrough) {
        this.failThrough(event, data);
      }
      return this;
    }
  }
  
  function prefix(name: string) {
    return "_" + name;
  }
  