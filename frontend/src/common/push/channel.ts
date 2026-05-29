// channel.ts
import { Dispatcher } from "@/common/push/dispatcher";
import { Connection } from "@/common/push/connection";

export class Channel extends Dispatcher {
    public subscribed = false;
    public subscribeCb: (() => void) | null = null;
    private queue: (() => void)[] = [];

    constructor(public connection: Connection, public channelName: string) {
        super();
    }

    processSubscribe() {
        if (this.connection.state !== "connected") return;
        this.subscribeCb?.();
    }

    processQueue() {
        if (this.connection.state !== "connected" || !this.subscribed) return;
        this.queue.forEach(fn => fn());
        this.queue = [];
    }

    trigger(event: string, data: any) {
        if (!event.startsWith("client-")) {
            throw new Error(`Event '${event}' should start with 'client-'`);
        }
        this.queue.push(() => {
            this.connection.send({ event, data, channel: this.channelName });
        });
        this.processQueue();
    }
}
