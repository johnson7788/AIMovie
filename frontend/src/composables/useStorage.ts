const storage = globalThis.localStorage;
const storagePrefix = 'SHORT-PLAY';
export const useStorage = () => {
    /**
     * 设置储存数据
     * @param key 键
     * @param data 值
     * @param expire 过期时间（秒）
     * @returns Promise
     */
    const set = (key: string, data: StorageInterface, expire?: number): Promise<boolean> => {
        return new Promise((resolve, reject) => {
            const obj = {
                expire: 0,
                data: data,
            }
            if (expire !== undefined) {
                obj.expire = Date.now() + expire * 1000
            }
            storage.setItem(getKey(key), JSON.stringify(obj));
            if (get(key) === null) {
                reject();
            } else {
                resolve(true);
            }
        })
    }
    /**
     * 获取储存数据
     * @param key 键
     * @returns StorageInterface
     */
    const get = (key: string): StorageInterface => {
        const data = storage.getItem(getKey(key));

        if (data === null) {
            return null;
        }
        const ret = JSON.parse(data);

        if (ret?.expire > 0 && ret?.expire < Date.now()) {
            return null;
        }
        return ret?.data;
    }
    /**
     * 删除储存数据
     * @param key 键
     * @returns Promise
     */
    const remove = (key: string): Promise<boolean> => {
        return new Promise((resolve, reject) => {
            storage.removeItem(getKey(key));
            if (get(key) === null) {
                resolve(true);
            } else {
                reject();
            }
        })
    }
    /**
     * 获取数据并删除
     * @param key 键
     * @returns StorageInterface
     */
    const getOnce = (key: string): StorageInterface => {
        const data = get(key);
        remove(key);
        return data;
    }
    /**
     * 获取真实存储键名
     * @param key 键
     * @returns string
     */
    const getKey = (key: string): string => {
        return `${storagePrefix}.${key}`;
    }
    return { set, get, remove, getOnce, getKey };
}