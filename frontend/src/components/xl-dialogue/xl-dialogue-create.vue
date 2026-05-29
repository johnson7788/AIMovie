<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useRefs, useWebConfigStore } from '@/stores';
import { ElMessage } from 'element-plus';
const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
const dialogueCreateDialogVisible = ref(false);
const storyboard = ref<any>();
const dialogueForm = ref<any>({
    id: '',
    drama_id: '',
    storyboard_id: '',
    actor_id: '',
    prosody_speed: 1,
    prosody_volume: 50,
    emotion: '',
    start_time: 0,
    end_time: 1000,
    content: '',
    actor: {
        name: "选择演员",
        headimg: "",
    }
});
const dialogueFormRules = ref<any>({
    actor_id: [{ required: true, message: '请选择演员', trigger: 'change' }],
    content: [{ required: true, message: '请输入对话内容', trigger: 'blur' }],
    prosody_speed: [{ required: true, message: '请选择语速', trigger: 'change' }],
    prosody_volume: [{ required: true, message: '请选择音量', trigger: 'change' }],
    emotion: [{ required: true, message: '请选择情感', trigger: 'change' }],
    start_time: [{ required: true, message: '请选择字幕&语音开始时间', trigger: 'change' }],
    end_time: [{ required: true, message: '请选择字幕结束时间', trigger: 'change' }],
});
const emit = defineEmits(['success']);
const dialogueFormRef = ref<any>();
const openDialogueCreateDialog = (item: any, form?: any) => {
    if (form) {
        dialogueForm.value = Object.assign(dialogueForm.value, form);
    }
    storyboard.value = item;
    dialogueForm.value.storyboard_id = item.id;
    dialogueForm.value.drama_id = item.drama_id;
    nextTick(() => {
        dialogueCreateDialogVisible.value = true;
    });
}
const closeDialogueCreateDialog = () => {
    dialogueFormRef.value?.resetFields();
    dialogueForm.value = {
        id: '',
        drama_id: '',
        storyboard_id: '',
        actor_id: '',
        prosody_speed: 1,
        prosody_volume: 50,
        emotion: '',
        start_time: 0,
        end_time: 1000,
        content: '',
        actor: {
            name: "选择演员",
            headimg: "",
        }
    };
    dialogueCreateDialogVisible.value = false;
}
const submitDialogueCreateLoading = ref(false);
const submitDialogueCreateDialog = () => {
    dialogueFormRef.value?.validate().then((valid: boolean) => {
        if (valid) {
            if (submitDialogueCreateLoading.value) return;
            submitDialogueCreateLoading.value = true;
            $http.post('/app/shortplay/api/StoryboardDialogue/save', dialogueForm.value).then((res: any) => {
                if (res.code === ResponseCode.SUCCESS) {
                    ElMessage.success(res.msg);
                    closeDialogueCreateDialog();
                    emit('success', storyboard.value, res.data);
                } else {
                    ElMessage.error(res.msg);
                }
            }).catch(() => {
                ElMessage.error('创建失败');
            }).finally(() => {
                submitDialogueCreateLoading.value = false;
            });
        }
    });
}
const actorPopoverRef = ref();
const actorButtonRef = ref();
const handleActorSelect = (actor: any) => {
    dialogueForm.value.actor_id = actor.id;
    dialogueForm.value.actor = actor;
    actorPopoverRef.value?.hide();
}
const speedFormatTooltip = (value: number) => {
    if (value === 1) {
        return '正常';
    }
    return `${value}x倍速`;
}
const volumeFormatTooltip = (value: number) => {
    if (value === 0) {
        return '静音';
    }
    if (value === 100) {
        return '最大';
    }
    if (value === 50) {
        return '正常';
    }
    if (value < 50) {
        return `-${value}%`;
    }
    return `+${value}%`;
}
const handleBeforeClose = () => {
    if (submitDialogueCreateLoading.value) return;
    closeDialogueCreateDialog();
}
defineExpose({
    open: openDialogueCreateDialog,
    close: closeDialogueCreateDialog
})
</script>
<template>
    <div v-if="dialogueCreateDialogVisible">
        <el-dialog v-model="dialogueCreateDialogVisible" class="generate-scene-dialog" draggable append-to-body
            :close-on-press-escape="false" :close-on-click-modal="false" :before-close="handleBeforeClose"
            width="min(100%,800px)">
            <template #header>
                <span class="font-weight-600" v-if="!dialogueForm.id">新增对话</span>
                <span class="font-weight-600" v-else>编辑对话</span>
            </template>
            <el-form label-position="top" :model="dialogueForm" :rules="dialogueFormRules" ref="dialogueFormRef"
                size="large">
                <div class="flex grid-gap-4">
                    <el-form-item label="演员" prop="actor" class="w-30">
                        <div class="flex flex-y-center grid-gap-2 rounded-4 p-4 bg-overlay w-100 pointer bg-hover-bg"
                            ref="actorButtonRef">
                            <el-avatar :src="dialogueForm.actor.headimg" :alt="dialogueForm.actor.name" shape="square"
                                class="icon-model"></el-avatar>
                            <span class="h10">{{ dialogueForm.actor.name }}</span>
                        </div>
                    </el-form-item>
                    <el-form-item label="对话内容" prop="content" class="flex-1">
                        <el-input type="textarea" v-model="dialogueForm.content" placeholder="请输入对话内容"
                            :autosize="{ minRows: 3, maxRows: 10 }" />
                    </el-form-item>
                </div>
                <div class="flex grid-gap-4">
                    <el-form-item label="语速" prop="prosody_speed" class="flex-1">
                        <div class="w-100 px-6">
                            <el-slider v-model="dialogueForm.prosody_speed" :step="0.1" show-stops :min="0.5" :max="2"
                                :format-tooltip="speedFormatTooltip" />
                        </div>
                    </el-form-item>
                    <el-form-item label="音量" prop="prosody_volume" class="flex-1">
                        <div class="w-100 px-6 pb-7">
                            <el-slider v-model="dialogueForm.prosody_volume" :step="1" :min="0" :max="100"
                                :format-tooltip="volumeFormatTooltip" :marks="{ 0: '静音', 100: '最大', 50: '正常' }" />
                        </div>
                    </el-form-item>
                </div>
                <el-form-item label="情感" prop="emotion">
                    <el-radio-group v-model="dialogueForm.emotion">
                        <el-radio v-for="item in WEBCONFIG?.enum?.voice_emotion" :key="item.value" :value="item.value"
                            border>{{
                                item.label }}</el-radio>
                    </el-radio-group>
                </el-form-item>
                <div class="flex grid-gap-4">
                    <el-form-item label="字幕&语音开始时间(毫秒)" prop="start_time">
                        <el-input-number v-model="dialogueForm.start_time" :min="0" :max="1000000" :step="100" />
                    </el-form-item>
                    <el-form-item label="字幕结束时间(毫秒)" prop="end_time">
                        <el-input-number v-model="dialogueForm.end_time" :min="0" :max="1000000" :step="100" />
                    </el-form-item>
                </div>
            </el-form>
            <template #footer>
                <div class="flex flex-center grid-gap-2 w-100">
                    <el-button type="info" @click="closeDialogueCreateDialog"
                        :disabled="submitDialogueCreateLoading">取消</el-button>
                    <div class="flex-1"></div>
                    <el-button type="success" @click="submitDialogueCreateDialog"
                        :loading="submitDialogueCreateLoading">提交</el-button>
                </div>
            </template>
        </el-dialog>
        <el-popover ref="actorPopoverRef" :virtual-ref="actorButtonRef" virtual-triggering placement="bottom-start"
            width="min(100vw,880px)" trigger="click">
            <xl-actor @select="handleActorSelect"
                :types="[{ label: '本集', value: 'episode' }, { label: '本剧', value: 'drama' }]"
                :query="{ drama_id: storyboard?.drama_id, episode_id: storyboard?.episode_id }" />
        </el-popover>
    </div>
</template>
<style lang="scss" scoped></style>