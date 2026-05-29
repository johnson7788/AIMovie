<template>
    <el-scrollbar height="90vh" @end-reached="handleScroll" :loading="loading">
        <div class="flex flex-y-center grid-gap-6 p-4 rounded-4 active pointer" v-for="item in list" :key="item.id"
            v-if="list.length > 0" @click="handleItemClick(item)">
            <div class="flex-shrink-0 position-relative">
                <div v-if="item.scene == 'announcement'" class="notice">
                    <el-icon color="#000" :size="26">
                        <BellFilled />
                    </el-icon>
                </div>
                <el-avatar :size="48" src="" v-else class="flex-shrink-0" alt="发斯蒂芬水电费" />
                <div class="unread" v-if="item.read_state == 0"></div>
            </div>
            <div class="flex flex-column grid-gap-2">
                <span class="h7 font-weight-600">{{ item.title }}</span>
                <span class="text-ellipsis-2 text-secondary">{{ item.subtitle }}</span>
            </div>
        </div>
        <div class="flex flex-center flex-column" v-else>
            <el-empty description="暂无消息" />
        </div>
    </el-scrollbar>

    <el-dialog v-model="dialogVisible"  append-to-body title="消息详情" width="600px" :close-on-click-modal="false">
        <div v-loading="detailLoading" class="detail-content">
            <div v-if="detailData" class="flex flex-column grid-gap-4">
                <div class="detail-header">
                    <h3 class="detail-title">{{ detailData.title }}</h3>
                    <div class="detail-meta text-secondary">
                        <span v-if="detailData.create_time">{{ detailData.create_time }}</span>
                    </div>
                </div>
                <div class="detail-body">
                    <div class="detail-text" v-html="detailData.content.content || detailData.subtitle"></div>
                </div>
            </div>
            <el-empty v-else description="暂无详情" />
        </div>
        <template #footer>
            <div class="flex flex-center ">
                <el-button color="var(--el-color-success)" @click="dialogVisible = false">我知道了</el-button>
            </div>
        </template>
    </el-dialog>
</template>
<script setup lang="ts">
import { $http } from '@/common/http'
import { ResponseCode } from '@/common/const'
const list = ref<any[]>([])
const query = ref({
    page: 1,
    limit: 10,
})
const loading = ref(false)
const total = ref(0)
const dialogVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<any>(null)

const getList = async () => {
    loading.value = true
    const res: any = await $http.get('/app/notification/api/Message/list', { params: query.value })
    if (res.code === ResponseCode.SUCCESS) {
        list.value = [...list.value, ...res.data.data]
        total.value = res.data.total
    }
    loading.value = false
}

const handleScroll = () => {
    if (query.value.page < total.value) {
        query.value.page++;
        getList();
    }
}

const handleItemClick = async (item: any) => {
    // 将未读状态修改为已读（仅在本地修改）
    if (item.read_state == 0) {
        const listItem = list.value.find(listItem => listItem.id === item.id)
        if (listItem) {
            listItem.read_state = 1
        }
    }
    dialogVisible.value = true
    detailData.value = null
    await getDetail(item.id)
}

const getDetail = async (id: number | string) => {
    detailLoading.value = true
    try {
        const res: any = await $http.get('/app/notification/api/Message/detail', { params: { id } })
        if (res.code === ResponseCode.SUCCESS) {
            detailData.value = res.data
        }
    } catch (error) {
        console.error('获取详情失败:', error)
    } finally {
        detailLoading.value = false
    }
}

defineExpose({
    open: () => {
        query.value.page = 1;
        list.value = [];
        getList();
    }
})

</script>
<style scoped lang="scss">
.active:hover {
    background: rgba(255, 255, 255, 0.1);
}

.notice {
    background-color: var(--el-color-success);
    width: 48px;
    height: 48px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}

.unread {
    background-color: var(--el-color-error);
    width: 12px !important;
    height: 12px !important;
    border-radius: 50%;
    position: absolute;
    top: 0px;
    right: 0px;
}

.detail-content {
    min-height: 200px;
}

.detail-header {
    padding-bottom: 8px;
}

.detail-title {
    margin: 0 0 8px 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--el-text-color-primary);
}

.detail-meta {
    font-size: 14px;
}

.detail-text {
    font-size: 14px;
    line-height: 1.6;
    color: var(--el-text-color-regular);
    word-wrap: break-word;
    white-space: pre-wrap;
}
</style>