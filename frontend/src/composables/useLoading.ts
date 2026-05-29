import { ElMessageBox, ElMessageBoxOptions } from "element-plus";
import XLLoading from "@/components/xl-loading/index.vue";
export const useLoading = (props: any) => {
    const xlLoadingRef = ref<any>(null);
    const options: ElMessageBoxOptions = {
        showClose: false,
        showCancelButton: false,
        showConfirmButton: false,
        customClass: 'x-loading-message-box',
        modalClass: 'x-loading-message-box-modal',
        closeOnPressEscape: false,
        closeOnClickModal: false,
        message: () => h(XLLoading, { ...props, ref: xlLoadingRef }),
    }
    const open = (): Promise<boolean> => {
        return new Promise((resolve) => {
            ElMessageBox(options).then((res: any) => {
                console.log('打开loading成功', res);
            }).catch(() => {
            });
            resolve(true);
        });
    }
    const close = () => {
        // @ts-ignore
        options.onVanish?.()
    }
    return { open, close, xlLoadingRef };
}