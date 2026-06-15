<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useRefs, useWebConfigStore } from '@/stores';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
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
        name: '',
        headimg: "",
    }
});
const dialogueFormRules = ref<any>({
    actor_id: [{ required: true, message: '', trigger: 'change' }],
    content: [{ required: true, message: '', trigger: 'blur' }],
    prosody_speed: [{ required: true, message: '', trigger: 'change' }],
    prosody_volume: [{ required: true, message: '', trigger: 'change' }],
    emotion: [{ required: true, message: '', trigger: 'change' }],
    start_time: [{ required: true, message: '', trigger: 'change' }],
    end_time: [{ required: true, message: '', trigger: 'change' }],
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
    // Update validation messages with current locale
    dialogueFormRules.value.actor_id[0].message = t('storyboard.selectActor');
    dialogueFormRules.value.content[0].message = t('storyboard.dialoguePlaceholder');
    dialogueFormRules.value.prosody_speed[0].message = t('storyboard.selectSpeed');
    dialogueFormRules.value.prosody_volume[0].message = t('storyboard.selectVolume');
    dialogueFormRules.value.emotion[0].message = t('storyboard.selectEmotion');
    dialogueFormRules.value.start_time[0].message = t('common.selectSpeed');
    dialogueFormRules.value.end_time[0].message = t('common.selectEndTime');
    // Set default actor name
    if (!dialogueForm.value.actor.name) {
        dialogueForm.value.actor.name = t('storyboard.selectActor');
    }
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
            name: t('storyboard.selectActor'),
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
                ElMessage.error(t('storyboard.createFail'));
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
        return t('storyboard.normal');
    }
    return t('storyboard.speedFormat', { value });
}
const volumeFormatTooltip = (value: number) => {
    if (value === 0) {
        return t('storyboard.mute');
    }
    if (value === 100) {
        return t('storyboard.max');
    }
    if (value === 50) {
        return t('storyboard.normal');
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
                <span class="font-weight-600" v-if="!dialogueForm.id">{{ t('storyboard.addDialogue') }}</span>
                <span class="font-weight-600" v-else>{{ t('storyboard.editDialogue') }}</span>
            </template>
            <el-form label-position="top" :model="dialogueForm" :rules="dialogueFormRules" ref="dialogueFormRef"
                size="large">
                <div class="flex grid-gap-4">
                    <el-form-item :label="t('storyboard.actor')" prop="actor" class="w-30">
                        <div class="flex flex-y-center grid-gap-2 rounded-4 p-4 bg-overlay w-100 pointer bg-hover-bg"
                            ref="actorButtonRef">
                            <el-avatar :src="dialogueForm.actor.headimg" :alt="dialogueForm.actor.name" shape="square"
                                class="icon-model"></el-avatar>
                            <span class="h10">{{ dialogueForm.actor.name }}</span>
                        </div>
                    </el-form-item>
                    <el-form-item :label="t('storyboard.dialogueContent')" prop="content" class="flex-1">
                        <el-input type="textarea" v-model="dialogueForm.content" :placeholder="t('storyboard.dialoguePlaceholder')"
                            :autosize="{ minRows: 3, maxRows: 10 }" />
                    </el-form-item>
                </div>
                <div class="flex grid-gap-4">
                    <el-form-item :label="t('storyboard.speedLabel')" prop="prosody_speed" class="flex-1">
                        <div class="w-100 px-6">
                            <el-slider v-model="dialogueForm.prosody_speed" :step="0.1" show-stops :min="0.5" :max="2"
                                :format-tooltip="speedFormatTooltip" />
                        </div>
                    </el-form-item>
                    <el-form-item :label="t('storyboard.volumeLabel')" prop="prosody_volume" class="flex-1">
                        <div class="w-100 px-6 pb-7">
                            <el-slider v-model="dialogueForm.prosody_volume" :step="1" :min="0" :max="100"
                                :format-tooltip="volumeFormatTooltip" :marks="{ 0: t('storyboard.mute'), 100: t('storyboard.max'), 50: t('storyboard.normal') }" />
                        </div>
                    </el-form-item>
                </div>
                <el-form-item :label="t('storyboard.emotionLabel')" prop="emotion">
                    <el-radio-group v-model="dialogueForm.emotion">
                        <el-radio v-for="item in WEBCONFIG?.enum?.voice_emotion" :key="item.value" :value="item.value"
                            border>{{
                                item.label }}</el-radio>
                    </el-radio-group>
                </el-form-item>
                <div class="flex grid-gap-4">
                    <el-form-item :label="t('storyboard.subtitleStart')" prop="start_time">
                        <el-input-number v-model="dialogueForm.start_time" :min="0" :max="1000000" :step="100" />
                    </el-form-item>
                    <el-form-item :label="t('storyboard.subtitleEnd')" prop="end_time">
                        <el-input-number v-model="dialogueForm.end_time" :min="0" :max="1000000" :step="100" />
                    </el-form-item>
                </div>
            </el-form>
            <template #footer>
                <div class="flex flex-center grid-gap-2 w-100">
                    <el-button type="info" @click="closeDialogueCreateDialog"
                        :disabled="submitDialogueCreateLoading">{{ t('common.cancel') }}</el-button>
                    <div class="flex-1"></div>
                    <el-button type="success" @click="submitDialogueCreateDialog"
                        :loading="submitDialogueCreateLoading">{{ t('common.submit') }}</el-button>
                </div>
            </template>
        </el-dialog>
        <el-popover ref="actorPopoverRef" :virtual-ref="actorButtonRef" virtual-triggering placement="bottom-start"
            width="min(100vw,880px)" trigger="click">
            <xl-actor @select="handleActorSelect"
                :types="[{ label: t('storyboard.thisEpisode'), value: 'episode' }, { label: t('storyboard.thisDrama'), value: 'drama' }]"
                :query="{ drama_id: storyboard?.drama_id, episode_id: storyboard?.episode_id }" />
        </el-popover>
    </div>
</template>
<style lang="scss" scoped></style>
