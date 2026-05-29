<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useUserStore } from '@/stores';
import DramaSvg from '@/svg/icon/drama.vue'
import ScriptSvg from '@/svg/icon/video-file.vue';
import IconUploadImageSvg from '@/svg/icon/icon-upload-image.vue';

import { ElMessage, ElMessageBox } from 'element-plus';
import router from '@/routers';
const userStore = useUserStore();
const SearchForm = reactive({
    page: 1,
    limit: 20,
    total: 0,
    title: '',
    script: 'all'
})
const list = ref<any[]>([]);
const handlePageChange = (page: number) => {
    SearchForm.page = page;
    getList();
}
const loading = ref(false);
const getList = () => {
    if (!userStore.hasLogin()) return;
    loading.value = true;
    list.value = [];
    $http.get('/app/shortplay/api/Works/index', { params: SearchForm }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            list.value = res.data.data;
            SearchForm.page = res.data.page;
            SearchForm.limit = res.data.limit;
            SearchForm.total = res.data.total;
        }
    }).finally(() => {
        loading.value = false;
    })
}
const handleItemClick = (item: any) => {
    router.push('/works/' + item.id);
}
const uploadCoverDialogVisible = ref(false);
const currentItem = ref<any>({});
const currentItemIndex = ref();
const uploadCoverRef = ref();
const uploadCoverSuccess = ref<any>({});
const openUploadCoverDialog = (item: any) => {
    currentItem.value = item;
    uploadCoverDialogVisible.value = true;
}
const uploadCoverLoading = ref(false);
const beforeUpload = (_file: File) => {
    if (!userStore.hasLogin()) {
        uploadCoverRef.value?.clearFiles();
        return false;
    }
    uploadCoverLoading.value = true;
    return true;
}
const handleUploadSuccess = (response: any) => {
    if (response.code === ResponseCode.SUCCESS) {
        switch (response.data.dir_name) {
            case 'drama/cover':
                uploadCoverSuccess.value = response.data;
                uploadCoverRef.value?.clearFiles();
                $http.post('/app/shortplay/api/Works/updateCover', {
                    id: currentItem.value.id,
                    cover: response.data.url,
                }).then((res: any) => {
                    if (res.code === ResponseCode.SUCCESS) {
                        ElMessage.success('上传封面成功');
                    } else {
                        ElMessage.info(res.msg);
                    }
                }).catch(() => {
                    ElMessage.error('上传封面失败');
                }).finally(() => {
                    uploadCoverDialogVisible.value = false;
                    uploadCoverLoading.value = false;
                    getList();
                });
                break;
        }
    } else {
        ElMessage.error(response.msg);
        uploadCoverLoading.value = false;
    }
}
const handleUploadError = () => {
    uploadCoverRef.value?.clearFiles();
    uploadCoverLoading.value = false;
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
            }
        });
    });
}
const modelButtonRef = ref();
const modelPopoverRef = ref();
const modelPopover = ref(false);
const selectedModel = ref<any>({ id: '' });
const modelLoading = ref(false);
const handleModelSelect = (item: any) => {
    selectedModel.value = item;
    modelLoading.value = true;
    $http.post('/app/shortplay/api/Generate/dramaCover', {
        id: currentItem.value.id,
        model_id: selectedModel.value.id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            list.value[currentItemIndex.value].cover_state = 1;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('生成封面失败');
    }).finally(() => {
        modelLoading.value = false;
        modelPopoverRef.value?.hide();
    });
}
const openGenerateCover = (e: Event, item: any, index: number) => {
    if (modelLoading.value) return;
    currentItem.value = item;
    currentItemIndex.value = index;
    modelButtonRef.value = e.target;
    nextTick(() => {
        modelPopover.value = true;
    })
}
onMounted(() => {
    getList();
})
</script>
<template>
    <el-form class="flex flex-center grid-gap-4 p-10" @submit.prevent="getList">
        <el-form-item class="mb-0">
            <xl-tabs v-model="SearchForm.script" class="text-info" @change="getList">
                <xl-tabs-item value="all">
                    <span class="h8 font-weight-600">全部</span>
                </xl-tabs-item>
                <xl-tabs-item value="drama">
                    <span class="h8 font-weight-600">剧本短剧</span>
                </xl-tabs-item>
                <xl-tabs-item value="script">
                    <span class="h8 font-weight-600">创意短剧</span>
                </xl-tabs-item>
            </xl-tabs>
        </el-form-item>
        <div class="flex-1"></div>
        <el-form-item class="mb-0">
            <el-input v-model="SearchForm.title" placeholder="搜索作品" clearable @change="getList">
                <template #suffix>
                    <el-icon>
                        <Search />
                    </el-icon>
                </template>
            </el-input>
        </el-form-item>
    </el-form>
    <template v-if="list.length > 0">
        <div
            class="grid-gap-4 px-10 grid-columns-xxl-8 grid-columns-xl-7 grid-columns-lg-6 grid-columns-md-5 grid-columns-sm-4 grid-columns-xs-3 grid-columns-p-2 grid-columns-p-1">
            <div class="grid-column-1 input-button rounded-4 border-2 border-solid flex flex-column drama-item"
                v-for="(item, index) in list" @click="handleItemClick(item)">
                <el-avatar :src="item.cover" class="drama-image">
                    <div class="flex flex-column grid-gap-1 flex-center" v-if="item.cover_state">
                        <el-icon size="40">
                            <Loading class="circular" />
                        </el-icon>
                        <span class="h10 font-weight-600 text-success">AI正在生成封面...</span>
                    </div>
                    <div class="flex flex-column grid-gap-1" v-else>
                        <span>{{ item.title }}</span>
                        <div class="h10 flex grid-gap-2 action-cover" v-if="!item.cover && !modelLoading">
                            <span class="text-success"
                                @click.stop="openGenerateCover($event, item, index)">AI生成封面</span>
                            <span class="text-info" @click.stop="openUploadCoverDialog(item)">上传封面</span>
                        </div>
                        <div class="h10 flex grid-gap-2 action-cover" v-else-if="modelLoading">
                            <span class="text-success">提交中...</span>
                        </div>
                    </div>
                </el-avatar>
                <div class="flex grid-gap-2 p-4 flex-center drama-title">
                    <el-icon size="46" class="bg rounded-4 p-2">
                        <DramaSvg v-if="item.script === 'drama'" />
                        <ScriptSvg v-else-if="item.script === 'script'" />
                    </el-icon>
                    <div class="flex-1 flex flex-column grid-gap-1">
                        <span class="font-weight-500 text-ellipsis-1">{{ item.title }}</span>
                        <span class="text-secondary h10 text-ellipsis-1">{{ item.create_time }}</span>
                    </div>
                </div>
                <span class="drama-episode">共{{ item.episode_num }}集</span>
                <el-icon class="delete-icon" @click.stop="handleDelete(item)">
                    <Delete />
                </el-icon>
            </div>
        </div>
        <div class="flex flex-center p-10">
            <el-pagination background layout="total, prev, pager, next,jumper" :total="SearchForm.total"
                :current-page="SearchForm.page" @current-change="handlePageChange" />
        </div>
    </template>
    <template v-else>
        <div class="flex flex-center grid-gap-4 p-10">
            <el-empty description="暂无作品" />
        </div>
    </template>
    <el-dialog v-model="uploadCoverDialogVisible" class="drama-dialog" draggable>
        <template #header>
            <span class="font-weight-600">《{{ currentItem.title }}》上传封面</span>
        </template>
        <el-upload ref="uploadCoverRef" class="input-upload flex-1" drag v-loading="uploadCoverLoading"
            :data="{ dir_name: 'drama/cover', dir_title: '剧本封面' }"
            :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')" :before-upload="beforeUpload"
            :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
            :on-success="handleUploadSuccess" :show-file-list="false" :on-error="handleUploadError">
            <template v-if="!uploadCoverSuccess.url">
                <el-icon class="el-icon--upload">
                    <IconUploadImageSvg />
                </el-icon>
                <div class="el-upload__text">
                    <span class="h10">拖拽剧本封面到此处或</span>
                    <span class="h10">点击上传</span>
                </div>
                <div class="el-upload__text">
                    <span class="h10">支持上传格式：</span>
                    <span class="h10">PNG, JPG, JPEG</span>
                </div>
                <div class="el-upload__text">
                    <span class="h10">封面比例：</span>
                    <span class="h10">4:3</span>
                </div>
            </template>
            <template v-else>
                <el-image :src="uploadCoverSuccess.url" class="image-cover" fit="contain"></el-image>
            </template>
        </el-upload>
    </el-dialog>
    <el-popover v-model:visible="modelPopover" ref="modelPopoverRef" :virtual-ref="modelButtonRef" virtual-triggering
        placement="bottom-start" width="min(100vw,380px)" trigger="click">
        <xl-models v-model="selectedModel.id" @select="handleModelSelect" scene="drama_cover" no-init
            v-loading="modelLoading" />
    </el-popover>
</template>
<style lang="scss" scoped>
.drama-item {
    cursor: pointer;
    position: relative;
    overflow: hidden;
    border-color: var(--el-bg-color-overlay);
    background-color: var(--el-bg-color-overlay);

    .action-cover {
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    }

    &:hover {
        border-color: var(--el-fill-color-dark);

        .action-cover {
            opacity: 1;
        }

        .delete-icon {
            opacity: 1;
        }

        .drama-image {
            :deep(img) {
                transform: scale(1.05);
            }
        }
    }

    .drama-title {
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        background: linear-gradient(180deg, rgba(0, 0, 0, 0.1) 0%, rgba(0, 0, 0, 0.50) 100%);
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .drama-image {
        width: 100%;
        height: 380px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;

        :deep(img) {
            transition: transform 0.15s;
            transform: scale(1);
        }
    }

    .drama-episode {
        position: absolute;
        top: 5px;
        left: 5px;
        background-color: rgba(0, 0, 0, 0.75);
        color: #FFFFFF;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 4px;
    }

    .delete-icon {
        height: 30px;
        width: 30px;
        position: absolute;
        top: 5px;
        right: 5px;
        background-color: rgba(0, 0, 0, 0.5);
        color: #FFFFFF;
        border-radius: 999px;
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    }
}
</style>