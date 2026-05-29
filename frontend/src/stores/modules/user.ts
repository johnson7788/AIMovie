import { useStorage } from '@/composables/useStorage';
import { onStoreageChange } from '@/common/functions';
import router from '@/routers';
export default () => {
    const storage = useStorage()
    const UserInfoStorageKey = 'USERINFO'
    const USERINFO = ref<UserInfoInterface>();
    const hasLogin = (): boolean => {
        return USERINFO.value !== undefined && USERINFO.value.token !== undefined && USERINFO.value.token !== null && USERINFO.value.token !== '';
    }
    const getToken = (): string | undefined => {
        return USERINFO.value?.token;
    }
    const setUserInfo = (UserInfo: UserInfoInterface): Promise<boolean | string> => {
        return new Promise((resolve, reject) => {
            USERINFO.value = UserInfo;
            storage.set(UserInfoStorageKey, UserInfo).then(() => {
                if (hasLogin()) {
                    resolve(true);
                } else {
                    reject('设置用户信息失败');
                }
            }).catch(() => {
                reject('设置本地储存失败')
            })
        })
    }
    const userListener = (): void => {
        onStoreageChange(storage.getKey(UserInfoStorageKey), (e?: StorageEvent) => {
            if (!e || e.newValue === null) {
                USERINFO.value = undefined;
            } else if (e.newValue !== null) {
                if (router.currentRoute.value.meta.login_access === true) {
                    initUserInfo();
                }
            }
        })
    }
    const initUserInfo = (): void => {
        const user = storage.get(UserInfoStorageKey)
        if (user !== null) {
            setUserInfo(user as UserInfoInterface)
        }
    }
    const clearUserInfo = (): Promise<boolean> => {
        USERINFO.value = undefined;
        return storage.remove(UserInfoStorageKey)
    }
    const hasPermission = (permission?: string | string[]): boolean => {
        if (USERINFO.value?.is_system) {
            return true;
        }
        if (!permission) {
            return true;
        }
        if (USERINFO.value?.permissions === undefined) {
            return false;
        }
        if (Array.isArray(permission)) {
            return permission.every(item => USERINFO.value?.permissions?.includes(item));
        }
        return USERINFO.value.permissions.includes(permission);
    }
    return {
        USERINFO,
        hasLogin,
        setUserInfo,
        initUserInfo,
        userListener,
        clearUserInfo,
        getToken,
        hasPermission
    };
}