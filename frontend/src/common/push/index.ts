// push.ts
import { Connection } from '@/common/push/connection';
import { Channel } from '@/common/push/channel';
import { ResponseCode } from '@/common/const';
import { $http } from '../http';


export interface PushOptions {
    url: string;
    app_key: string;
    auth?: string;
    heartbeat?: number;
    pingTimeout?: number;
}
export class Push {
    static instances: Push[] = [];
    private pingTimeoutTimer: number | null = null;
    public channels: Record<string, Channel> = {};
    public connection: Connection | null = null;

    constructor(private config: PushOptions) {
        this.config.heartbeat = this.config.heartbeat ?? 25000;
        this.config.pingTimeout = this.config.pingTimeout ?? 10000;
        Push.instances.push(this);
        this.createConnection();
    }

    private checkoutPing = () => {
        setTimeout(() => {
            if (this.connection?.state === "connected") {
                this.connection.send({ event: "pusher:ping", data: {} });
                if (this.pingTimeoutTimer) {
                    clearTimeout(this.pingTimeoutTimer);
                }
                this.pingTimeoutTimer = window.setTimeout(() => {
                    this.connection?.closeAndClean();
                    if (this.connection && !this.connection.doNotConnect) {
                        this.connection.waitReconnect();
                    }
                }, this.config.pingTimeout);
            }
        }, this.config.heartbeat);
    };
    /**
     * 订阅频道
     * @param channelName 频道名称
     * @param api 接口函数,当频道为私有频道时,需要传递接口函数
     * @returns 频道实例
     */
    subscribe(channelName: string) {
        if (this.channels[channelName]) return this.channels[channelName];

        if (channelName.indexOf('private-') === 0) {
            return this.createPrivateChannel(channelName);
        }
        if (channelName.indexOf('presence-') === 0) {
            return this.createPresenceChannel(channelName);
        }
        return this.createChannel(channelName);
    }


    createChannel(channelName: string) {
        const channel = new Channel(this.connection!, channelName);
        this.channels[channelName] = channel;

        channel.subscribeCb = () => {
            this.connection?.send({ event: "pusher:subscribe", data: { channel: channelName } });
        };
        channel.processSubscribe();
        return channel;
    }

    createPrivateChannel(channelName: string) {
        let channel = new Channel(this.connection!, channelName);
        this.channels[channelName] = channel;
        channel.subscribeCb = () => {
            if (!this.config.auth) return;
            $http.post(this.config.auth, { channel_name: channelName, socket_id: this.connection!.socket_id }).then((res: any) => {
                if (res.code === ResponseCode.SUCCESS) {
                    res.data.channel = channelName;
                    this.connection!.send({ event: "pusher:subscribe", data: res.data });
                } else {
                    channel.emit('subscription_error', res.msg);
                }
            }).catch((err: any) => {
                channel.emit('subscription_error', err.message);
            });
        };
        channel.processSubscribe();
        return channel;
    }

    createPresenceChannel(channelName: string) {
        return this.createPrivateChannel(channelName);
    }

    unsubscribe(channelName: string) {
        if (this.channels[channelName]) {
            delete this.channels[channelName];
            if (this.connection?.state === "connected") {
                this.connection.send({ event: "pusher:unsubscribe", data: { channel: channelName } });
            }
        }
    }

    unsubscribeAll() {
        Object.keys(this.channels).forEach(name => this.unsubscribe(name));
        this.channels = {};
    }

    private createConnection() {
        if (this.connection) {
            throw new Error("Connection already exist");
        }

        this.connection = new Connection({
            url: this.config.url,
            app_key: this.config.app_key,
            onOpen: () => {
                this.connection!.state = "connecting";
                this.checkoutPing();
            },
            onMessage: ev => {
                if (this.pingTimeoutTimer) {
                    clearTimeout(this.pingTimeoutTimer);
                    this.pingTimeoutTimer = null;
                }
                const params = JSON.parse(ev.data);
                const { event, channel: channelName } = params;

                if (event === "pusher:pong") {
                    this.checkoutPing();
                    return;
                }
                if (event === "pusher:connection_established") {
                    this.connection!.socket_id = JSON.parse(params.data).socket_id;
                    this.connection!.state = "connected";
                    this.subscribeAll();
                }
                const channel = this.channels[channelName];
                if (channel) channel.emit(event, JSON.parse(params.data));
            },
            onClose: () => {
                Object.values(this.channels).forEach(c => (c.subscribed = false));
            },
            onError: () => {
                Object.values(this.channels).forEach(c => (c.subscribed = false));
            }
        });
    }

    private subscribeAll() {
        if (this.connection?.state !== "connected") return;
        Object.values(this.channels).forEach(ch => ch.processSubscribe());
    }

    disconnect() {
        if (this.connection) {
            this.connection.doNotConnect = true;
            this.connection.close();
        }
    }
}
