import { ElMessageBox } from "element-plus"
import type { ElMessageBoxOptions } from "element-plus"
import XVcode from "@/components/x-vcode/index.vue"

export const useVcode = () => {
    const btnText = ref('获取验证码')
    const btnDisabled = ref(false)
    let timer: any;
    let timerCount = 60;
    const open = (params: any) => {
        return new Promise((resolve, reject) => {
            const options: ElMessageBoxOptions = {
                showClose: false,
                showCancelButton: false,
                showConfirmButton: false,
                customClass: 'x-login-message-box',
                customStyle: {
                    '--el-messagebox-width': 'min(375px,100%)',
                    '--el-messagebox-height': '300px',
                },
                closeOnPressEscape: false,
                closeOnClickModal: false,
                message: () => h(XVcode, {
                    data: params,
                    onSuccess: (res: any) => {
                        btnText.value = '重新获取'
                        btnDisabled.value = true
                        timer = setInterval(() => {
                            btnText.value = `重新获取(${timerCount--}s)`
                            if (timerCount <= 0) {
                                clearInterval(timer)
                                timer = undefined
                                btnText.value = '获取验证码'
                                btnDisabled.value = false
                                timerCount = 60
                            }
                        }, 1000)
                        // @ts-ignore
                        options.onVanish?.()
                        resolve(res)
                    },
                    onClose: () => {
                        // @ts-ignore
                        options.onVanish?.()
                        if (timer) {
                            clearInterval(timer)
                            timer = undefined
                        }
                        reject('关闭验证码')
                    }
                }),
            }
            ElMessageBox(options)
                .then(() => {
                })
                .catch((error) => {
                    reject(error)
                })
        })
    }
    return {
        open,
        btnText,
        btnDisabled
    }
}