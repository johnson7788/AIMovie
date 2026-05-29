// connection.ts
import { Dispatcher } from '@/common/push/dispatcher';
export interface ConnectionOptions {
    url: string;
    app_key: string;
    onOpen?: (ev: Event) => void;
    onMessage?: (ev: MessageEvent) => void;
    onClose?: (ev: CloseEvent) => void;
    onError?: (ev: Event) => void;
}
export class Connection extends Dispatcher {
    private options: ConnectionOptions;
    private websocket: WebSocket | null = null;
    public state: "initialized" | "connecting" | "connected" | "disconnected" =
        "initialized";
    public doNotConnect = false;
    public reconnectInterval = 1;
    private reconnectTimer: number | null = null;
    public socket_id?: string;

    constructor(options: ConnectionOptions) {
        super();
        this.options = options;
        this.connect();
    }

    private updateNetworkState(state: typeof this.state) {
        const oldState = this.state;
        this.state = state;
        if (oldState !== state) {
            this.emit("state_change", { previous: oldState, current: state });
        }
    }

    connect() {
        this.doNotConnect = false;
        if (this.state === "connected") {
            console.log(`networkState is "${this.state}" and do not need connect`);
            return;
        }
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        this.closeAndClean();

        const { url, app_key, onOpen, onMessage, onClose, onError } = this.options;
        const ws = new WebSocket(`${url}/app/${app_key}`);

        this.updateNetworkState("connecting");

        ws.onopen = ev => {
            this.reconnectInterval = 1;
            if (this.doNotConnect) {
                this.updateNetworkState("disconnected");
                ws.close();
                return;
            }
            onOpen?.(ev);
        };

        if (onMessage) {
            ws.onmessage = onMessage;
        }

        ws.onclose = ev => {
            this.cleanupHandlers(ws);
            this.updateNetworkState("disconnected");
            if (!this.doNotConnect) this.waitReconnect();
            onClose?.(ev);
        };

        ws.onerror = ev => {
            this.close();
            if (!this.doNotConnect) this.waitReconnect();
            onError?.(ev);
        };

        this.websocket = ws;
    }

    private cleanupHandlers(ws: WebSocket) {
        ws.onmessage = null;
        ws.onopen = null;
        ws.onclose = null;
        ws.onerror = null;
    }

    closeAndClean() {
        if (this.websocket) {
            this.cleanupHandlers(this.websocket);
            try {
                this.websocket.close();
            } catch { }
            this.updateNetworkState("disconnected");
        }
    }

    waitReconnect() {
        if (this.state === "connected" || this.state === "connecting") return;
        if (!this.doNotConnect) {
            this.updateNetworkState("connecting");
            if (this.reconnectTimer) clearTimeout(this.reconnectTimer);

            this.reconnectTimer = window.setTimeout(() => {
                this.connect();
            }, this.reconnectInterval);

            this.reconnectInterval =
                this.reconnectInterval < 1000
                    ? 1000
                    : Math.min(this.reconnectInterval * 2, 2000);
        }
    }

    send(data: any) {
        let dataString = JSON.stringify(data);
        if (this.state !== "connected" || !this.websocket) {
            console.trace(`networkState is "${this.state}", can not send ${dataString}`);
            return;
        }
        this.websocket.send(dataString);
    }

    close() {
        this.updateNetworkState("disconnected");
        this.websocket?.close();
    }
}
