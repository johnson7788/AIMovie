export const usePush = () => {
    const { appContext } = getCurrentInstance()!
    const global = appContext.config.globalProperties;
    const channels = new Map<string, any>();
    const subscribe = (channel: string, callback: (data: any) => void) => {
        if (global.$push) {
            const channelItem = global.$push.subscribe(channel);
            channelItem.on('message', callback);
            channelItem.on('pusher_internal:subscription_succeeded', function () {
                console.log('channels complete info subscription succeeded');
            });
            channelItem.on('subscription_error', function (message: any) {
                console.log('channels complete info subscription error', message);
            });
            channels.set(channel, channelItem);
        }
    }
    const unsubscribe = (channel: string) => {
        if (global.$push) {
            global.$push.unsubscribe(channel);
            channels.delete(channel);
        }
    }
    const unsubscribeAll = () => {
        channels.forEach((_channelItem, channel) => {
            if (global.$push) {
                global.$push.unsubscribe(channel);
            }
            channels.delete(channel);
        });
    }
    return {
        subscribe,
        unsubscribe,
        unsubscribeAll,
    }
}