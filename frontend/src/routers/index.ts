
import { ResponseCode } from "@/common/const";
import { $http } from "@/common/http";
import { useRefs, useUserStore, useWebConfigStore } from "@/stores";
import { createRouter, createWebHashHistory } from "vue-router";
import { ElMessageBox } from "element-plus";
import { useStorage } from "@/composables/useStorage";
const router = createRouter({
    history: createWebHashHistory(),
    routes: [
        {
            path: '/main',
            name: 'main',
            component: () => import("@/layouts/control.vue"),
            meta: {
                title: '主页',
            },
            redirect: '/',
            children: [
                {
                    path: '/',
                    name: 'index',
                    component: () => import("@/pages/index/index.vue"),
                    meta: {
                        title: '首页',
                        menu: 'index',
                    }
                },
                {
                    path: '/creative',
                    name: 'creative',
                    component: () => import("@/pages/creative/index.vue"),
                    meta: {
                        title: '创意圈',
                        menu: 'creative',
                    }
                },
                {
                    path: '/actor',
                    name: 'actor',
                    component: () => import("@/pages/actor/index.vue"),
                    meta: {
                        title: '演员库',
                        menu: 'actor',
                    }
                },
                {
                    path: '/voice',
                    name: 'voice',
                    component: () => import("@/pages/voice/index.vue"),
                    meta: {
                        title: '声音库',
                        menu: 'voice',
                    }
                },
                {
                    path: '/user',
                    name: 'user',
                    component: () => import("@/pages/user/index.vue"),
                    meta: {
                        title: '个人中心',
                        menu: 'user',
                    }
                },
                {
                    path: '/square',
                    name: 'square',
                    component: () => import("@/pages/works/square.vue"),
                    meta: {
                        title: '广场',
                        menu: 'square',
                    }
                },
                {
                    path: '/works/:drama_id',
                    name: 'works-detail',
                    component: () => import("@/pages/works/drama.vue"),
                    meta: {
                        title: '短剧详情',
                        menu: 'works',
                    },
                    beforeEnter: (to, _from, next) => {
                        const userStore = useUserStore();
                        if (to.params.drama_id && userStore.hasLogin()) {
                            next()
                        } else {
                            next({ name: 'works' })
                        }
                    },
                },
                {
                    path: '/play/:drama_id/:episode_id',
                    name: 'play-detail',
                    component: () => import("@/pages/play/index.vue"),
                    meta: {
                        title: '短剧播放',
                    },
                    beforeEnter: (to, _from, next) => {
                        if (to.params.drama_id && to.params.episode_id) {
                            next()
                        } else {
                            next({ name: 'index' })
                        }
                    },
                },
                {
                    path: '/voice/create',
                    name: 'voice-create',
                    component: () => import("@/pages/voice/create.vue"),
                    meta: {
                        title: '创建声音',
                    }
                }
            ]
        },
        {
            path: '/code',
            name: 'user-code',
            component: () => import("@/pages/user/code.vue"),
            meta: {
                title: '邀请码',
                menu: 'user',
            }
        },
        {
            path: '/article/:article',
            name: 'article',
            component: () => import("@/pages/article/content.vue"),
            meta: {
                title: '文章详情',
                menu: 'article',
            }
        },
        {
            path: '/generate/:drama_id/:episode_id?',
            name: 'generate',
            component: () => import("@/pages/generate/index.vue"),
            meta: {
                title: '生成剧本',
            },
            redirect: (to) => {
                return to.params.drama_id && to.params.episode_id ? `/generate/drama/${to.params.drama_id}/${to.params.episode_id}` : '/';
            },
            children: [
                {
                    path: '/generate/drama/:drama_id/:episode_id?',
                    name: 'generate-drama',
                    component: () => import("@/pages/generate/drama/index.vue"),
                    meta: {
                        title: '剧本调整',
                    },
                    beforeEnter: (to, _from, next) => {
                        const userStore = useUserStore();
                        if (!to.params.drama_id || !to.params.episode_id || !userStore.hasLogin()) {
                            next({ name: 'index' })
                        } else {
                            next()
                        }
                    },
                },
                {
                    path: '/generate/actors/:drama_id/:episode_id?',
                    name: 'generate-actors',
                    component: () => import("@/pages/generate/actors/index.vue"),
                    meta: {
                        title: '剧本调整',
                    },
                    beforeEnter: (to, _from, next) => {
                        const userStore = useUserStore();
                        if (!to.params.drama_id || !to.params.episode_id || !userStore.hasLogin()) {
                            next({ name: 'index' })
                        } else {
                            next()
                        }
                    },
                },
                {
                    path: '/generate/props/:drama_id/:episode_id?',
                    name: 'generate-props',
                    component: () => import("@/pages/generate/props/index.vue"),
                    meta: {
                        title: '剧本调整',
                    },
                    beforeEnter: (to, _from, next) => {
                        const userStore = useUserStore();
                        if (!to.params.drama_id || !to.params.episode_id || !userStore.hasLogin()) {
                            next({ name: 'index' })
                        } else {
                            next()
                        }
                    },
                },
                {
                    path: '/generate/scene/:drama_id/:episode_id?',
                    name: 'generate-scene',
                    component: () => import("@/pages/generate/scene/index.vue"),
                    meta: {
                        title: '剧本调整',
                    },
                    beforeEnter: (to, _from, next) => {
                        const userStore = useUserStore();
                        if (!to.params.drama_id || !to.params.episode_id || !userStore.hasLogin()) {
                            next({ name: 'index' })
                        } else {
                            next()
                        }
                    },
                },
                {
                    path: '/generate/storyboard/:drama_id/:episode_id?',
                    name: 'generate-storyboard',
                    component: () => import("@/pages/generate/storyboard/index.vue"),
                    meta: {
                        title: '剧本调整',
                    },
                    beforeEnter: (to, _from, next) => {
                        const userStore = useUserStore();
                        if (!to.params.drama_id || !to.params.episode_id || !userStore.hasLogin()) {
                            next({ name: 'index' })
                        } else {
                            next()
                        }
                    },
                }
            ]
        }
    ],
})
const getWebConfig = () => {
    return new Promise((resolve, reject) => {
        $http.get('/app/control/api/Public/config').then((res: any) => {
            if (res.code === ResponseCode.SUCCESS) {
                const webConfigStore = useWebConfigStore();
                webConfigStore.setWebConfig(res.data as WebConfigInterface);
                resolve(res.data);
            } else {
                reject();
            }
        }).catch(() => {
            reject();
        });
    })
}

// 验证邀请码是否被使用
const checkInvitationCode = async (code: string): Promise<boolean> => {
    try {
        const res: any = await $http.get(`/app/user/api/User/checkInvitationCode?code=${code}`);
        // 如果接口返回成功，说明邀请码可用（未被使用）
        if (res.code === ResponseCode.SUCCESS) {
            return true;
        } else {
            // 接口返回失败，说明邀请码已被使用或无效
            return false;
        }
    } catch (error: any) {
        // 如果接口返回错误，说明邀请码已被使用或无效
        const errorMsg = error?.response?.data?.msg || error?.msg || '邀请码验证失败';
        // 如果错误信息明确表示邀请码已被使用或无效，返回 false
        if (errorMsg.includes('已被使用') || errorMsg.includes('无效') || errorMsg.includes('不存在')) {
            return false;
        }
        // 其他错误也视为验证失败
        return false;
    }
}

// 处理邀请码验证（只在第一次访问或刷新时验证）
const handleInvitationCode = async (to: any, from: any) => {
    const storage = useStorage();
    // 判断是否是第一次访问或刷新（from.name 为 null 或 undefined 表示刷新或首次访问）
    const isFirstVisit = from.name === null || from.name === undefined;

    // 只在首次访问或刷新时验证，且 URL 中有 code 参数
    if (isFirstVisit && to.query.code) {
        const code = to.query.code as string;
        // 验证邀请码是否被使用
        try {
            const isValid = await checkInvitationCode(code);
            if (isValid) {
                // 邀请码有效，存入缓存
                storage.set('ICODE', code);
            } else {
                // 邀请码已被使用或无效，提示用户
                ElMessageBox({
                    title: '温馨提示',
                    message: '邀请码无效或已被使用',
                    type: 'warning',
                });
            }
        } catch (error) {
            // 验证失败，提示用户
            ElMessageBox({
                title: '温馨提示',
                message: '邀请码验证失败',
                type: 'error',
            });
        }
    }
}
router.beforeEach(async (to, from, next) => {
    const webConfigStore = useWebConfigStore();
    const { WEBCONFIG } = useRefs(webConfigStore);
    webConfigStore.initWebConfig();
    if (!WEBCONFIG.value?.web_name) {
        await getWebConfig().then(() => {
            console.log('初始化网站配置成功');
        }).catch(() => {
            console.error('初始化网站配置失败');
        });
    }

    // 处理邀请码验证（只在第一次访问或刷新时验证）
    await handleInvitationCode(to, from);

    const userStore = useUserStore();
    userStore.initUserInfo();
    const { USERINFO } = useRefs(userStore);
    const whiteList = ['index', 'article']
    if (!userStore.hasLogin() && !whiteList.includes(to.name as string)) {
        return next({ name: 'index' })
    }
    next()
})
router.afterEach((to, _from) => {
    const { WEBCONFIG } = useWebConfigStore();
    if (to.name == 'index') {
        globalThis.document.title = `${WEBCONFIG?.web_title}`;
        return;
    }
    let subTitle = '';
    if (WEBCONFIG.web_title) {
        subTitle = ` - ${WEBCONFIG.web_title}`;
    } else if (WEBCONFIG.web_name) {
        subTitle = ` - ${WEBCONFIG.web_name}`;
    }
    globalThis.document.title = `${to.meta?.title}${subTitle}`
})
export default router