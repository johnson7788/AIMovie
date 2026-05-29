<template>
    <el-scrollbar height="100%" wrap-class="flex-1" @end-reached="scrollBarEndReached">
        <div v-loading="loading" class="flex-1">
            <div class="flex flex-wrap grid-gap-6" v-if="list.length > 0">
                <div class="box flex-1" v-for="item in list" :key="item.id" @click="handleItemClick(item)">
                    <div class="box-delete" @click.stop="handleDelete(item)">
                        <el-icon>
                            <Delete />
                        </el-icon>
                    </div>
                    <span class="box-drama-episode ">
                        共{{ item.episode_num }}集
                    </span>
                    <el-avatar :src="item.cover" class="box-image" shape="square">
                        <div class="flex flex-column grid-gap-1 flex-center" v-if="item.cover_state">
                            <el-icon size="40">
                                <Loading class="circular" />
                            </el-icon>
                            <span class="h10 font-weight-600 text-success">AI正在生成封面...</span>
                        </div>
                    </el-avatar>
                    <div class="box-content">
                        <div class="box-content-icon">
                            <el-icon :size="30">
                                <DramaSvg />
                            </el-icon>
                        </div>
                        <div class="box-content-title">
                            <span class="h8 font-weight-500 text-ellipsis-1">{{ item.title }}</span>
                            <span class="h9 text-secondary font-weight-500">{{ item.create_time }}</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="flex flex-center" v-else>
                <el-empty description="暂无作品" />
            </div>
        </div>
    </el-scrollbar>
</template>
<script setup lang="ts">

import DramaSvg from '@/svg/icon/drama.vue'
import { $http } from '@/common/http';
import { ResponseCode } from '@/common/const';
import { useUserStore } from '@/stores';
import { ElMessageBox, ElMessage } from 'element-plus';
import router from '@/routers';

const userStore = useUserStore();
const SearchForm = reactive({
    page: 1,
    limit: 20,
    title: '',
    script: 'all'
})
const loading = ref(false);
const list = ref<any[]>([]);
const total = ref<number>(0);

const getList = () => {
    if (!userStore.hasLogin()) return;
    loading.value = true;
    $http.get('/app/shortplay/api/Works/index', { params: SearchForm }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            list.value = [...list.value, ...res.data.data];
            SearchForm.page = res.data.page;
            SearchForm.limit = res.data.limit;
            total.value = res.data.total;
        }
    }).finally(() => {
        loading.value = false;
    })
}

const scrollBarEndReached = () => {
    if (list.value.length >= total.value) return;
    SearchForm.page++;
    getList();
}

const handleDelete = (item: any) => {
    ElMessageBox.confirm('确定删除该作品吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
    }).then(() => {
        $http.post('/app/shortplay/api/Drama/delete', {
            id: item.id,
        }).then((res: any) => {
            if (res.code === ResponseCode.SUCCESS) {
                ElMessage.success('删除作品成功');
                // 删除成功后重新加载列表
                list.value = [];
                SearchForm.page = 1;
                getList();
            }
        });
    });
}
const handleItemClick = (item: any) => {
    router.push('/works/' + item.id);
}
onMounted(() => {
    getList();
})
</script>
<style scoped lang="scss">
.box {
    background-color: #1E1E1E;
    border-radius: 20px;
    overflow: hidden;
    position: relative;
    min-width: 340px;
    cursor: pointer;
    transition: all 0.3s ease;
    max-width: 340px;

    // &:hover {
    //     transform: scale(1.03);
    // }

    &-drama-episode {
        position: absolute;
        top: 15px;
        left: 15px;
        background: rgba(0, 0, 0, 0.5);
        color: #FFFFFF;
        font-size: 12px;
        padding: 4px 8px;
        border-radius: 4px;
    }

    &:hover {
        .box-delete {
            display: flex;
        }
    }

    &-delete {
        position: absolute;
        top: 10px;
        right: 10px;
        width: 26px;
        height: 26px;
        background: rgba(0, 0, 0, 0.5);
        border-radius: 50%;
        display: none;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s ease;

        &:hover {
            background: var(--el-color-success);
            color: #000;
        }
    }

    &-image {
        width: 100%;
        height: 200px;
        background-color: #2D2D2D;
    }

    &-content {
        padding: 16px;
        display: flex;
        gap: 12px;
        align-items: center;

        &-icon {
            width: 46px;
            height: 46px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        &-title {
            display: flex;
            flex-direction: column;
            gap: 4px;
            font-size: 14px;
            color: #fff;
            font-weight: 500;
        }
    }
}
</style>