<script setup lang="ts">
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import HomeSvg from '@/svg/tabs/home.vue'
import SquareSvg from '@/svg/tabs/square.vue'
import UserSvg from '@/svg/tabs/user.vue'
import HomeActiveSvg from '@/svg/tabs/home-active.vue'
import SquareActiveSvg from '@/svg/tabs/square-active.vue'
import UserActiveSvg from '@/svg/tabs/user-active.vue'
import IconLogoSvg from '@/svg/icon/icon-logo.vue'
import NoticeSvg from '@/svg/tabs/notice.vue'
import NoticeActiveSvg from '@/svg/tabs/notice-active.vue'
import router from '@/routers'
import { RouteLocationNormalized } from 'vue-router'
import { useStateStore, useRefs, useUserStore ,useWebConfigStore} from '@/stores'
import { useLogin } from '@/composables/useLogin'
import XlNotice from '@/components/xl-notice/index.vue'
import { Close } from '@element-plus/icons-vue'
const iconMap: Record<string, any> = {
    ...ElementPlusIconsVue,
    HomeSvg,
    SquareSvg,
    UserSvg,
    HomeActiveSvg,
    SquareActiveSvg,
    UserActiveSvg,
    IconLogoSvg,
    NoticeSvg,
    NoticeActiveSvg,
}
const menus = ref([
    {
        type: 'router',
        name: '首页',
        path: '/',
        menu: 'index',
        icon: 'HomeSvg',
        activeIcon: 'HomeActiveSvg'
    },
    {
        type: 'router',
        name: '创意圈',
        path: '/square',
        menu: 'square',
        icon: 'SquareSvg',
        activeIcon: 'SquareActiveSvg'
    },
    {
        type: 'router',
        name: '通知',
        path: '/notice',
        menu: 'notice',
        icon: 'NoticeSvg',
        activeIcon: 'NoticeActiveSvg'
    },
    {
        type: 'router',
        name: '个人中心',
        path: '/user',
        menu: 'user',
        icon: 'UserSvg',
        activeIcon: 'UserActiveSvg'
    }
])
const { WEBCONFIG } = useRefs(useWebConfigStore())
// 根据当前路由获取对应的菜单标识
const getCurrentMenu = (route: RouteLocationNormalized): string => {
    // 优先使用路由 meta 中的 menu 字段
    if (route.meta?.menu) {
        return route.meta.menu as string
    }
    // 如果 meta.menu 不存在，根据路由路径匹配菜单
    const matchedMenu = menus.value.find(menu => menu.path === route.path)
    return matchedMenu?.menu || menus.value[0].menu
}

const currentMenu = ref(getCurrentMenu(router.currentRoute.value))
watch(() => router.currentRoute.value, (newRoute: RouteLocationNormalized) => {
    currentMenu.value = getCurrentMenu(newRoute)
}, { immediate: true })
const stateStore = useStateStore()
const { STATE } = useRefs(stateStore)
const userStore = useUserStore()
const login = useLogin()
const noticePopoverVisible = ref(false)
const noticeRef = ref<any>(null)


// 不需要登录验证的菜单路径
const noLoginMenus = ['/']

// 获取视频格式
const getVideoType = (url: string): string => {
    if (!url) return ''
    const extension = url.split('.').pop()?.toLowerCase()
    switch (extension) {
        case 'webm':
            return 'video/webm'
        case 'mp4':
        case 'mov':
            return 'video/mp4'
        case 'ogg':
            return 'video/ogg'
        default:
            return 'video/mp4'
    }
}

// 动态获取背景视频地址
const backgroundVideoUrl = computed(() => {
    return WEBCONFIG.value?.project_background_video_url || '/aimovie/static/image/bg.mov'
})

// 获取视频类型
const videoType = computed(() => {
    return getVideoType(backgroundVideoUrl.value)
})

// 处理菜单点击
const handleMenuClick = (menu: any, event: MouseEvent) => {
    // 如果是通知菜单，打开弹窗
    if (menu.menu === 'notice') {
        event.preventDefault()
        noticePopoverVisible.value = true
        noticeRef.value?.open()
        return
    }
    // 如果是首页或已登录，直接跳转
    if (noLoginMenus.includes(menu.path) || userStore.hasLogin()) {
        router.push(menu.path)
        return
    }
    // 未登录且不是首页，阻止默认跳转，打开登录弹窗
    event.preventDefault()
    login.open()
}
const videoRef = ref<HTMLVideoElement | null>(null)
onMounted(() => {
    requestIdleCallback(() => {
        const video = videoRef.value
        if (video) {
            video.play()
        }
    })
})
</script>
<template>
    <div class="control-layouts" :class="{ 'bg ': $route.path === '/' }">
        <!-- 背景视频 -->
        <video ref="videoRef" v-show="$route.path === '/' && backgroundVideoUrl" preload="metadata"
            class="control-layouts-bg-video" autoplay loop muted playsinline>
            <source :src="backgroundVideoUrl" :type="videoType">
        </video>
        <transition name="blur-fade">
            <div class="control-layouts-header-bg" v-if="$route.path === '/' && STATE.InputFocusState"></div>
        </transition>
        <div class="control-layouts-header">
            <div class="control-layouts-header-logo pointer" @click="router.push('/')">
                <!-- <el-icon alt="logo" size="30" class="control-layouts-header-logo-img"> -->
                <IconLogoSvg />
                <!-- </el-icon> -->
            </div>
            <div class="flex-1"></div>
            <x-header-tools />
        </div>
        <div class="control-layouts-menu">
            <ul class="control-layouts-menu-list">
                <li v-for="menu in menus" :key="menu.path" class="control-layouts-menu-list-item"
                    :class="{ 'control-layouts-menu-list-item-selected': currentMenu === menu.menu }">
                    <template v-if="menu.type === 'router' && menu.path">
                        <el-tooltip class="box-item" effect="dark" :content="menu.name" placement="right">
                            <div class="control-layouts-menu-list-item-link" @click="handleMenuClick(menu, $event)">
                                <el-icon size="26">
                                    <component
                                        :is="currentMenu === menu.menu ? iconMap[menu.activeIcon] : iconMap[menu.icon]" />
                                </el-icon>
                            </div>
                        </el-tooltip>
                    </template>
                    <template v-else-if="menu.type === 'link' && menu.path">
                        <a :href="menu.path" class="control-layouts-menu-list-item-link" target="_blank">
                            <el-icon>
                                <component :is="iconMap[menu.icon]" />
                            </el-icon>
                            <!-- <span>{{ menu.name }}</span> -->
                        </a>
                    </template>
                    <!-- <template v-else>
                        <div class="control-layouts-menu-list-item-divider"></div>
                    </template> -->
                </li>
            </ul>
        </div>
        <router-view />
        <el-popover :visible="noticePopoverVisible" width="430px" placement="right-end" :show-arrow="false"
            trigger="click" title="消息中心" popper-style="height:90dvh;margin-top:10dvh;inset:auto auto 5dvh 88px;">
            <div class="position-relative">
                <XlNotice ref="noticeRef" />
                <div class="position-absolute top--10 right-4 pointer z-10">
                    <el-icon :size="20" @click="noticePopoverVisible = false">
                        <Close />
                    </el-icon>
                </div>
            </div>
            <template #reference>
                <div></div>
            </template>
        </el-popover>

    </div>
</template>
<style scoped lang="scss">
.control-layouts {
    --xl-header-height: 72px;
    --xl-menu-width: 94px;
    padding: var(--xl-header-height) 0 0 var(--xl-menu-width);
    transition: padding 0.3s ease-in-out;
    position: relative;

    &-bg-video {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: center;
        z-index: 0;
        pointer-events: none;
    }

    &-header {
        width: 100%;
        height: var(--xl-header-height);
        // background-color: rgba(var(--el-bg-color-rgb-r), var(--el-bg-color-rgb-g), var(--el-bg-color-rgb-b), 0.35);
        // backdrop-filter: blur(20px);
        position: fixed;
        top: 0;
        left: 0;
        z-index: 10;
        // box-shadow: 0 0 0 2px var(--el-border-color);
        padding: 0 20px;
        display: flex;
        align-items: center;
        gap: 20px;

        &-logo {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: start;
            gap: 10px;

            &-img {
                font-size: 30px;
                width: 100%;
                height: 22px;
            }

            &-text {
                font-size: 16px;
                font-weight: 500;
            }
        }
    }

    &-menu {
        width: var(--xl-menu-width);
        height: calc(100vh - var(--xl-header-height));
        // background-color: var(--el-bg-color);
        position: fixed;
        top: calc(var(--xl-header-height) + 2px);
        left: 0;
        z-index: 10;
        padding: 20px 0;
        display: flex;
        align-items: center;
        justify-content: center;

        &-list {
            width: 60px;
            margin: 0;
            padding: 24px 0px;
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 28px;

            background: rgba(0, 0, 0, 0.04);
            border-radius: 200px 200px 200px 200px;
            border: 0.1px solid rgba(0, 0, 0, 0.12);

            &-item {
                width: 100%;
                list-style: none;
                padding: 0px;
                margin: 0;
                border-radius: 10px;

                // &-divider {
                //     width: 100%;
                //     height: 1px;
                //     background: linear-gradient(to right, transparent, transparent, var(--el-border-color), transparent, transparent);
                // }

                &-selected {
                    // background-color: rgba(13, 242, 131, 0.10);

                    .control-layouts-menu-list-item-link {
                        color: var(--el-color-white);
                    }
                }

                &-link {
                    width: 100%;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 4px;
                    text-decoration: none;
                    color: #8C8C8C;
                    padding: 6px 0;
                    cursor: pointer;
                    user-select: none;
                    -webkit-user-select: none;
                    -moz-user-select: none;
                    -ms-user-select: none;
                }
            }
        }
    }
}

.control-layouts-header-bg {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    backdrop-filter: blur(8px);
    z-index: 1;
    pointer-events: none;
}

.blur-fade-enter-active,
.blur-fade-leave-active {
    transition: opacity 0.5s ease, backdrop-filter 0.5s ease;
}

.blur-fade-enter-from,
.blur-fade-leave-to {
    opacity: 0;
    backdrop-filter: blur(0px);
}

.blur-fade-enter-to,
.blur-fade-leave-from {
    opacity: 1;
    backdrop-filter: blur(8px);
}
</style>
<style>
.el-popover {
    --el-popover-bg-color: rgba(0, 0, 0, 0.04);
    --el-popover-border-color: rgba(3255, 255, 255, 0.3);
    --el-box-shadow-light: none;
    --el-popover-border-radius: 20px;
    --el-popover-padding: 20px;
    backdrop-filter: blur(8px);
    overflow: hidden;
}
</style>