import { ElMessageBox } from "element-plus"
import type { ElMessageBoxOptions } from "element-plus"
import { h } from "vue"
import XLogin from "@/components/x-login/index.vue"
export const useLogin = () => {
    const open = () => {
        const options: ElMessageBoxOptions = {
            showClose: false,
            showCancelButton: false,
            showConfirmButton: false,
            customClass: 'x-login-message-box',
            closeOnPressEscape: false,
            closeOnClickModal: false,
            message: () => h(XLogin, {
                onSuccess: (e: any) => {
                    // @ts-ignore
                    options.onVanish?.()
                },
                onClose: () => {
                    console.log('关闭登录')
                    // @ts-ignore
                    options.onVanish?.()
                }
            }),
        }
        ElMessageBox(options)
            .then(() => {
                console.log('打开登录成功')
            })
            .catch(() => {
                console.log('打开登录失败')
            })
    }
    const close = () => {
        console.log('关闭登录')
        ElMessageBox.close()
    }
    return {
        open,
        close
    }
}