<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import router from '@/routers';
import { Action, ElMessage, ElMessageBox, MessageBoxState } from 'element-plus';
import IconPlaySvg from '@/svg/icon/icon-play.vue';
const props = withDefaults(defineProps<{
    find: any
}>(), {
    find: () => ({}),
});
const emit = defineEmits(['update']);
const find = ref<any>(props.find);
watch(() => props.find, (newVal) => {
    find.value = newVal
})
const handleItemClick = (item: any) => {
    router.push('/generate/drama/' + props.find.id + '/' + item.id);
}
const createEpisodeLoading = ref(false);
const continueEpisode = () => {
    if (createEpisodeLoading.value) return;
    createEpisodeLoading.value = true;
    $http.post('/app/shortplay/api/Generate/continueEpisode', {
        ...createEpisodeForm,
        drama_id: props.find.id
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            find.value.continue_episode_state = 1;
            cancelCreateEpisode();
        } else {
            ElMessage.error(res.msg);
        }
    }).finally(() => {
        createEpisodeLoading.value = false;
    })
}
const createEpisodeForm = reactive({
    id: '',
    model_id: '',
    title: '',
    content: '',
    episode_no: '',
    episode_sum: 1,
});
const createEpisodeFormRules = {
    title: [{ required: true, message: '请输入分集标题', trigger: 'blur' }],
    content: [{ required: true, message: '请输入分集内容', trigger: 'blur' }],
};
const createEpisodeFormRef = ref<any>(null);
const createEpisodeDialogVisible = ref(false);
const createEpisodeAction = ref('form');
const createEpisode = () => {
    createEpisodeDialogVisible.value = true;
    createEpisodeForm.episode_sum = props.find.episode_sum - props.find.episode_num;
}
const createEpisodeIndex = ref();
const handleEditEpisode = (item: any, index: any) => {
    createEpisodeDialogVisible.value = true;
    createEpisodeAction.value = 'form';
    createEpisodeIndex.value = index;
    createEpisodeForm.id = item.id;
    createEpisodeForm.title = item.title;
    createEpisodeForm.content = item.content;
    createEpisodeForm.episode_no = item.episode_no;
}
const nextEpisode = () => {
    if (createEpisodeIndex.value < find.value.episodes.length - 1) {
        createEpisodeIndex.value++;
    }
    handleEditEpisode(find.value.episodes[createEpisodeIndex.value], createEpisodeIndex.value);
}
const prevEpisode = () => {
    if (createEpisodeIndex.value > 0) {
        createEpisodeIndex.value--;
    }
    handleEditEpisode(find.value.episodes[createEpisodeIndex.value], createEpisodeIndex.value);
}
const cancelCreateEpisode = () => {
    createEpisodeFormRef.value?.resetFields?.();
    createEpisodeAction.value = 'form';
    createEpisodeForm.id = '';
    createEpisodeForm.model_id = '';
    createEpisodeForm.title = '';
    createEpisodeForm.content = '';
    createEpisodeForm.episode_no = '';
    createEpisodeForm.episode_sum = 1;
    createEpisodeDialogVisible.value = false;
}
const submitCreateEpisode = () => {
    if (createEpisodeAction.value === 'ai') {
        if (!createEpisodeForm.model_id) {
            ElMessage.error('请选择AI模型');
            return;
        }
        continueEpisode();
        return;
    }
    createEpisodeFormRef.value.validate().then((valid: boolean) => {
        if (valid) {
            if (createEpisodeLoading.value) return;
            createEpisodeLoading.value = true;
            $http.post('/app/shortplay/api/DramaEpisode/create', {
                ...createEpisodeForm,
                drama_id: props.find.id,
            }).then((res: any) => {
                if (res.code === ResponseCode.SUCCESS) {
                    ElMessage.success(res.msg);
                    cancelCreateEpisode();
                    emit('update');
                } else {
                    ElMessage.error(res.msg);
                }
            }).catch(() => {
                ElMessage.error('创建分集失败');
            }).finally(() => {
                createEpisodeLoading.value = false;
            })
        }
    })
}
const handleDeleteEpisode = (item: any) => {
    ElMessageBox.confirm(`确定删除第${item.episode_no}集【${item.title}】吗？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        beforeClose: (action: Action, instance: MessageBoxState, done: () => void) => {
            if (action === 'confirm') {
                instance.confirmButtonLoading = true;
                $http.post('/app/shortplay/api/DramaEpisode/delete', {
                    id: item.id,
                    drama_id: props.find.id,
                }).then((res: any) => {
                    if (res.code === ResponseCode.SUCCESS) {
                        emit('update');
                        done();
                    } else {
                        ElMessage.error(res.msg);
                    }
                }).catch(() => {
                    ElMessage.error('删除分集失败');
                }).finally(() => {
                    instance.confirmButtonLoading = false;
                });
            } else {
                done();
            }
        }
    })
}
const handleDownloadEpisode = (item: any) => {
    const el = document.createElement('a');
    el.href = item.video_path;
    el.download = item.drama_id + '_' + item.episode_id + '.mp4';
    el.target = '_blank';
    el.click();
}
</script>
<template>
    <div
        class="grid-gap-4 px-10 grid-columns-xxl-8 grid-columns-xl-7 grid-columns-lg-6 grid-columns-md-5 grid-columns-sm-4 grid-columns-xs-3 grid-columns-p-2 grid-columns-p-1">
        <div class="grid-column-1 input-button rounded-4 flex flex-column episode-item"
            v-for="(item, index) in find.episodes" :key="item.id">
            <div class="position-relative episode-image">
                <el-avatar :src="item.cover" class="episode-image">
                    <div class="flex flex-column grid-gap-4 flex-center pointer" @click.stop="handleItemClick(item)">
                        <span class="h10">{{ item.title }}</span>
                        <span class="h10 text-ellipsis-10 text-info episode-content">{{ item.outline }}</span>
                    </div>
                </el-avatar>
                <el-icon class="play-icon pointer" v-if="item.video_path" size="36"
                    @click="router.push('/play/' + props.find.id + '/' + item.id+'?view=share')">
                    <IconPlaySvg />
                </el-icon>
            </div>
            <div class="flex grid-gap-2 p-4 flex-center episode-title">
                <span class="font-weight-600">第 {{ item.episode_no }} 集</span>
            </div>
            <el-popover placement="bottom-end" popper-class="episode-popover" width="100px" :teleported="false"
                @click.stop>
                <template #reference>
                    <el-icon class="more-icon pointer" @click.stop>
                        <More />
                    </el-icon>
                </template>
                <div class="flex flex-column grid-gap-2 h10" @click.stop>
                    <span class="text-center py-2 pointer" @click.stop="handleItemClick(item)">工程</span>
                    <span class="text-center py-2 pointer" @click.stop="handleEditEpisode(item, index)">编辑</span>
                    <span class="text-center py-2 pointer" v-if="item.video_path"
                        @click.stop="handleDownloadEpisode(item)">下载</span>
                    <span class="text-center py-2 pointer" @click.stop="handleDeleteEpisode(item)">删除</span>
                </div>
            </el-popover>
        </div>
        <template v-if="find.episode_num < find.episode_sum">
            <div class="grid-column-1 input-button rounded-4 flex flex-column episode-item" @click="createEpisode"
                v-if="!find.continue_episode_state" v-loading="createEpisodeLoading">
                <div class="episode-image flex flex-center flex-column grid-gap-4">
                    <el-icon size="36">
                        <Plus />
                    </el-icon>
                    <span class="h10 text-info">添加第{{ find.episode_num + 1 }}集</span>
                    <span class="h10 text-info">全 {{ find.episode_sum }} 集，更新至 {{ find.episode_num }} 集</span>
                </div>
            </div>
            <div class="grid-column-1 input-button rounded-4 flex flex-column episode-item" v-else>
                <div class="episode-image flex flex-center flex-column grid-gap-4">
                    <el-icon size="36">
                        <Loading class="circular" />
                    </el-icon>
                    <span class="h10 text-info">续写分集中...</span>
                </div>
            </div>
        </template>
    </div>
    <el-dialog v-model="createEpisodeDialogVisible" class="generate-scene-dialog" draggable width="min(100%,800px)"
        @close="cancelCreateEpisode">
        <template #header>
            <span class="font-weight-600" v-if="!createEpisodeForm.id">创建分集</span>
            <span class="font-weight-600" v-else>编辑第{{ createEpisodeForm.episode_no }}集</span>
        </template>
        <el-segmented v-model="createEpisodeAction" :disabled="createEpisodeLoading"
            :options="[{ label: '填写分集', value: 'form' }, { label: 'AI续写', value: 'ai' }]" class="tabs-segmented border"
            v-if="!createEpisodeForm.id" />
        <el-form v-if="createEpisodeAction === 'form'" label-position="top" :model="createEpisodeForm"
            :rules="createEpisodeFormRules" ref="createEpisodeFormRef">
            <el-form-item label="分集标题" prop="title">
                <el-input v-model="createEpisodeForm.title" placeholder="请输入分集标题" />
            </el-form-item>
            <el-form-item label="分集内容" prop="content">
                <el-input v-model="createEpisodeForm.content" type="textarea" :autosize="{ minRows: 10, maxRows: 30 }"
                    placeholder="请输入分集内容" />
            </el-form-item>
        </el-form>
        <div class="flex flex-column grid-gap-4" v-if="createEpisodeAction === 'ai'">
            <el-alert title="灵感缺乏？使用AI续写" type="success" :closable="false" />
            <xl-models v-model="createEpisodeForm.model_id" scene="creative_episode" no-init
                v-loading="createEpisodeLoading" />
        </div>
        <template #footer>
            <div class="flex flex-center grid-gap-2 w-100">
                <el-button type="info" @click="cancelCreateEpisode" :disabled="createEpisodeLoading">取消</el-button>
                <div class="flex-1"></div>
                <el-button type="primary" @click="prevEpisode"
                    :disabled="createEpisodeLoading || createEpisodeIndex <= 0"
                    v-if="createEpisodeForm.id">上一集</el-button>
                <el-button type="primary" @click="nextEpisode"
                    :disabled="createEpisodeLoading || createEpisodeIndex >= find.episodes.length - 1"
                    v-if="createEpisodeForm.id">下一集</el-button>
                <template v-if="!createEpisodeForm.id && createEpisodeAction === 'ai'">
                    <el-input-number v-model="createEpisodeForm.episode_sum" :min="1"
                        :max="find.episode_sum - find.episode_num" :disabled="createEpisodeLoading"
                        v-if="!createEpisodeForm.id && createEpisodeAction === 'ai'">
                        <template #prefix>
                            <span>集数</span>
                        </template>
                    </el-input-number>
                    <el-button type="success" @click="submitCreateEpisode" :disabled="createEpisodeLoading">生成{{
                        createEpisodeForm.episode_sum }}集</el-button>
                </template>
                <template v-else>
                    <el-button type="success" @click="submitCreateEpisode"
                        :disabled="createEpisodeLoading">提交</el-button>
                </template>
            </div>
        </template>
    </el-dialog>
</template>
<style lang="scss" scoped>
.episode-item {
    position: relative;
    overflow: hidden;

    &:hover {
        border-color: var(--el-fill-color-dark);

        .more-icon {
            opacity: 1;
        }

        .episode-image {
            :deep(img) {
                transform: scale(1.05);
            }
        }
    }

    .episode-title {
        width: 100%;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .episode-image {
        width: 100%;
        height: 220px;
        border-radius: 8px;
        --el-avatar-bg-color: #1E1E1E;
        background-color: var(--el-avatar-bg-color);

        :deep(img) {
            transition: transform 0.15s;
            transform: scale(1);
        }

        .episode-content {
            width: 90%;
            line-height: 1.5;
            letter-spacing: 2px;

            &::before,
            &::after {
                content: '“';
                color: var(--el-color-success);
                line-height: 1;
                font-size: 2em;
                font-weight: 600;
            }

            &::after {
                content: '”';
            }
        }
    }

    .more-icon {
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

    .play-icon {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }
}
</style>