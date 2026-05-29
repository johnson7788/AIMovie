<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useUserStore } from '@/stores';
import { ElLoading, ElMessageBox, LoadingInstance } from 'element-plus';
import router from '@/routers';
import Episodes from '@/pages/works/modules/episodes.vue';
import Details from '@/pages/works/modules/details.vue';
import Actors from '@/pages/works/modules/actors.vue';
import Props from '@/pages/works/modules/props.vue';
import { usePush } from '@/composables/usePush';
const userStore = useUserStore();
const SearchForm = reactive({
    ...router.currentRoute.value.query,
    id: router.currentRoute.value.params.drama_id as string,
})
const find = ref<any>({});
const loading = ref(true);
let loadingInstance: LoadingInstance;
const { subscribe, unsubscribeAll } = usePush();
const addListener = () => {
    if (find.value.id) {
        subscribe('private-continueepisode-' + find.value.id, (res: any) => {
            console.log('channels complete info message', res);
            getDetails();
        });
        subscribe('private-generatedramacover-' + find.value.id, (res: any) => {
            console.log('channels complete info message', res);
            getDetails();
        });
    }
}
const getDetails = () => {
    if (!userStore.hasLogin()) return;
    if (find.value.id) {
        loading.value = true;
    } else {
        loadingInstance = ElLoading.service({
            lock: true,
            text: '加载中...',
        });
    }
    $http.get('/app/shortplay/api/Works/details', { params: SearchForm }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            find.value = res.data;
            addListener();
        } else {
            loadingInstance?.close();
            ElMessageBox.confirm(res.msg, '提示', {
                confirmButtonText: '重新加载',
                cancelButtonText: '返回',
                type: 'warning',
            }).then(() => {
                getDetails();
            }).catch(() => {
                router.push('/user');
            });
        }
    }).catch(() => {
        loadingInstance?.close();
        ElMessageBox.confirm('加载失败，请重新加载', '提示', {
            confirmButtonText: '重新加载',
            cancelButtonText: '返回',
            type: 'warning',
        }).then(() => {
            getDetails();
        }).catch(() => {
            router.push('/user');
        });
    }).finally(() => {
        loading.value = false;
        loadingInstance?.close();
    })
}
const action = ref('episodes');
const actionComponent = computed(() => {
    return {
        episodes: Episodes,
        actors: Actors,
        props: Props,
        details: Details,
    }[action.value];
})
onMounted(() => {
    getDetails();
})
onUnmounted(() => {
    unsubscribeAll();
})
</script>
<template>
    <el-skeleton :loading="loading" animated>
        <template #template>
            <div class="flex flex-column grid-gap-10 p-10">
                <div class="flex">
                    <el-skeleton-item variant="text" style="height: 45px;width:100px;" />
                    <div class="flex-1 flex flex-center">
                        <el-skeleton-item variant="text" style="height: 45px;width: 520px;" />
                    </div>
                </div>
                <div
                    class="grid-gap-4 grid-columns-xxl-8 grid-columns-xl-7 grid-columns-lg-6 grid-columns-md-5 grid-columns-sm-4 grid-columns-xs-3 grid-columns-p-2 grid-columns-p-1">
                    <el-skeleton-item variant="text" style="height: 240px" class="grid-column-1 flex flex-column"
                        v-for="i in 20" :key="i" />
                </div>
            </div>
        </template>
        <template #default>
            <div class="flex flex-y-center flex-x-space-between grid-gap-4 p-10">
                <div class="flex-1 flex flex-flex-start">
                    <div class="flex grid-gap-4 flex-y-center pointer" @click="router.push('/user')">
                        <el-icon>
                            <ArrowLeft />
                        </el-icon>
                        <span class="h8 font-weight-600">{{ find.title }}</span>
                    </div>
                </div>
                <el-segmented v-model="action" :disabled="loading"
                    :options="[{ label: '分集', value: 'episodes', component: Episodes }, { label: '角色库', value: 'actors', component: 'Actors' }, { label: '物品库', value: 'props', component: 'Props' }, { label: '详情', value: 'details', component: 'Details' }]"
                    class="tabs-segmented border" />
                <div class="flex-1"></div>
            </div>
            <component :is="actionComponent" :find="find" @update="getDetails" />
        </template>
    </el-skeleton>
</template>
<style lang="scss" scoped></style>