import { StoreGeneric, defineStore, storeToRefs } from 'pinia'
import WebConfigStore from "@/stores/modules/webconfig";
export const useWebConfigStore = defineStore('webconfig', WebConfigStore)
import StateStore from "@/stores/modules/state";
export const useStateStore = defineStore('state', StateStore)
import UserStore from "@/stores/modules/user";
export const useUserStore = defineStore('user', UserStore)
import ModelStore from "@/stores/modules/model";
export const useModelStore = defineStore('model', ModelStore)
export const useRefs = (store: StoreGeneric) => {
    return storeToRefs(store);
}