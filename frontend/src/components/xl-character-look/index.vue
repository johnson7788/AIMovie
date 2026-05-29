<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useUserStore, useRefs } from '@/stores';
import { usePush } from '@/composables/usePush';
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const props = withDefaults(defineProps<{
    query?: any
    types?: any[]
}>(), {
    query: () => ({}),
    types: () => ([]),
});
const emit = defineEmits(['select']);
const CharacterLookSearch = reactive({
    type: 'all',
    description: '',
    actor_id: '',
    ...props.query,
})
const characterLookList = ref<any[]>([]);
const characterLookDialogVisible = ref(false);
const loading = ref(false);
const getCharacterLookList = () => {
    loading.value = true;
    characterLookList.value = [];
    $http.get('/app/shortplay/api/CharacterLook/index', { params: CharacterLookSearch }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            currentCharacterLook.value = {};
            characterLookList.value = res.data;
        }
    }).finally(() => {
        loading.value = false;
    })
}
const currentCharacterLook = ref<any>({});
const handleCharacterLookItemClick = (item: any) => {
    if (item.status_enum.value !== 'generated') return ElMessage.info('该装扮还未初始化完成');
    currentCharacterLook.value = item;
}
const handleCharacterLookConfirm = () => {
    characterLookDialogVisible.value = false;
    emit('select', {
        ...currentCharacterLook.value,
        type: CharacterLookSearch.type,
        actor_costume_model_id: actorCostumeModel.value.id,
        actor_costume_three_view_model_id: actorCostumeThreeViewModel.value.id,
    });
}
const modelLoading = ref(false);
const actorCostumeButtonRef = ref();
const actorCostumePopoverRef = ref();
const actorCostumeModel = ref<any>({});
const handleActorCostumeSelect = (item: any) => {
    actorCostumeModel.value = item;
    actorCostumePopoverRef.value?.hide();
}
const actorCostumeThreeViewButtonRef = ref();
const actorCostumeThreeViewPopoverRef = ref();
const actorCostumeThreeViewModel = ref<any>({});
const handleActorCostumeThreeViewSelect = (item: any) => {
    actorCostumeThreeViewModel.value = item;
    actorCostumeThreeViewPopoverRef.value?.hide();
}
const openCharacterLookDialog = (options?: any) => {
    if (options) {
        if (options?.actor) {
            CharacterLookSearch.actor_id = options.actor.id;
        } else {
            CharacterLookSearch.actor_id = '';
        }
    }
    getCharacterLookList();
    addListener();
    characterLookDialogVisible.value = true;
}
const handleBeforeClose = (done: any) => {
    if (modelLoading.value) return;
    done();
}
const initCurrentCharacterLook = ref();
const initModelDialogVisible = ref(false);
const initLoading = ref(false);
const handleCharacterLookInit = (item: any) => {
    initCurrentCharacterLook.value = item;
    initModelDialogVisible.value = true;
}
const handleCharacterLookInitSubmit = () => {
    if (initLoading.value) return;
    initLoading.value = true;
    $http.post('/app/shortplay/api/Generate/characterLookCostume', initCurrentCharacterLook.value).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            getCharacterLookList();
            initModelDialogVisible.value = false;
        } else {
            ElMessage.info(res.msg);
        }
    })
        .catch(() => {
            ElMessage.error('初始化失败');
        })
        .finally(() => {
            initLoading.value = false;
        })
}
const { subscribe, unsubscribeAll } = usePush();
const addListener = () => {
    subscribe('private-generatecharacterlookcostume-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = characterLookList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            getCharacterLookList();
        }
    });
}
onUnmounted(() => {
    unsubscribeAll();
})
const xlCharacterLookCreateRef = ref();
defineExpose({
    open: openCharacterLookDialog,
})
</script>
<template>
    <div>
        <el-dialog v-model="characterLookDialogVisible" class="generate-scene-dialog" draggable width="min(100%,800px)"
            :close-on-press-escape="false" :close-on-click-modal="false" :before-close="handleBeforeClose">
            <template #header>
                <span class="font-weight-600">演员装扮</span>
            </template>
            <div class="flex flex-column grid-gap-4" v-loading="modelLoading">
                <el-form class="flex flex-center grid-gap-4" @submit.prevent="getCharacterLookList">
                    <el-form-item class="mb-0">
                        <xl-tabs v-model="CharacterLookSearch.type" class="text-info" @change="getCharacterLookList">
                            <xl-tabs-item value="all">全部</xl-tabs-item>
                            <xl-tabs-item value="drama">本剧</xl-tabs-item>
                            <xl-tabs-item value="episode">本集</xl-tabs-item>
                            <xl-tabs-item value="actor" v-if="CharacterLookSearch.actor_id">演员装扮</xl-tabs-item>
                        </xl-tabs>
                    </el-form-item>
                    <div class="flex-1"></div>
                    <el-form-item class="mb-0">
                        <el-input v-model="CharacterLookSearch.description" placeholder="搜索装扮" clearable
                            @change="getCharacterLookList">
                            <template #suffix>
                                <el-icon>
                                    <Search />
                                </el-icon>
                            </template>
                        </el-input>
                    </el-form-item>
                </el-form>
                <el-scrollbar height="40vh" v-loading="loading" v-if="characterLookList.length > 0 || loading">
                    <div class="grid-columns-5 grid-gap-4">
                        <div v-if="CharacterLookSearch.type != 'actor'"
                            class="grid-column-1 flex flex-column flex-center grid-gap-2 character-look-item"
                            @click="xlCharacterLookCreateRef?.open?.();">
                            <div class="character-look-item-image flex flex-center bg-overlay rounded-4">
                                <el-icon size="50" class="border rounded-4 p-4 border-2">
                                    <Plus />
                                </el-icon>
                            </div>
                            <span>新增装扮</span>
                        </div>
                        <div class="grid-column-1 flex flex-column flex-center grid-gap-2 character-look-item"
                            :class="{ 'character-look-item-active': currentCharacterLook.id === item.id }"
                            v-for="item in characterLookList" @click="handleCharacterLookItemClick(item)">
                            <template v-if="item.component === 'actor'">
                                <el-avatar :src="item.headimg" shape="square" fit="fill"
                                    class="character-look-item-image" />
                                <span>{{ item.characterLook.title }}</span>
                            </template>
                            <template v-else>
                                <el-avatar :src="item.status_enum.value === 'generated' ? item.costume_url : ''"
                                    shape="square" fit="fill" class="character-look-item-image bg-mosaic">
                                    <template v-if="item.status_enum.value === 'pending'">
                                        <div class="flex flex-column flex-center grid-gap-2">
                                            <el-icon>
                                                <Loading class="circular" />
                                            </el-icon>
                                            <span class="text-info h10">初始化中</span>
                                        </div>
                                    </template>
                                    <template v-else-if="item.status_enum.value === 'initializing'">
                                        <el-button type="success" size="small" text
                                            @click.stop="handleCharacterLookInit(item)">立即初始化</el-button>
                                    </template>
                                </el-avatar>
                                <span>{{ item.title }}</span>
                            </template>
                        </div>
                    </div>
                </el-scrollbar>
                <el-empty v-else description="暂无装扮">
                    <el-button type="success" bg text @click="xlCharacterLookCreateRef?.open?.();">新增装扮</el-button>
                </el-empty>
            </div>
            <template #footer>
                <el-button bg text @click="characterLookDialogVisible = false" :loading="modelLoading">取消</el-button>
                <div class="flex-1"></div>
                <template v-if="CharacterLookSearch.type !== 'actor'">
                    <div class="flex flex-center grid-gap-2 input-button rounded-4 py-2 px-6"
                        ref="actorCostumeButtonRef">
                        <template v-if="!actorCostumeModel.id">
                            <el-icon alt="角色换装" class="icon-model" color="var(--el-color-success)">
                                <IconModelSvg />
                            </el-icon>
                            <span class="h10">选择角色换装模型</span>
                        </template>
                        <template v-else>
                            <el-avatar :src="actorCostumeModel.icon" :alt="actorCostumeModel.name" shape="square"
                                class="icon-model"></el-avatar>
                            <span class="h10">{{ actorCostumeModel.name }}</span>
                        </template>
                    </div>
                    <div class="flex flex-center grid-gap-2 input-button rounded-4 py-2 px-6"
                        ref="actorCostumeThreeViewButtonRef">
                        <template v-if="!actorCostumeThreeViewModel.id">
                            <el-icon alt="角色换装三视图" class="icon-model" color="var(--el-color-success)">
                                <IconModelSvg />
                            </el-icon>
                            <span class="h10">选择角色换装三视图模型</span>
                        </template>
                        <template v-else>
                            <el-avatar :src="actorCostumeThreeViewModel.icon" :alt="actorCostumeThreeViewModel.name"
                                shape="square" class="icon-model"></el-avatar>
                            <span class="h10">{{ actorCostumeThreeViewModel.name }}</span>
                        </template>
                    </div>
                <el-button type="success" @click="handleCharacterLookConfirm" :loading="modelLoading"
                    :disabled="!currentCharacterLook.id">
                    <span>确认选择</span>
                </el-button>
            </template>
        </el-dialog>
        <el-popover ref="actorCostumePopoverRef" :virtual-ref="actorCostumeButtonRef" virtual-triggering
            placement="bottom-start" width="min(100vw,380px)" trigger="click">
            <xl-models v-model="actorCostumeModel.id" @select="handleActorCostumeSelect" scene="actor_costume" />
        </el-popover>
        <el-popover ref="actorCostumeThreeViewPopoverRef" :virtual-ref="actorCostumeThreeViewButtonRef"
            virtual-triggering placement="bottom-start" width="min(100vw,380px)" trigger="click">
            <xl-models v-model="actorCostumeThreeViewModel.id" @select="handleActorCostumeThreeViewSelect"
                scene="actor_costume_three_view" />
        </el-popover>
        <xl-character-look-create ref="xlCharacterLookCreateRef" :query="props.query"
            @success="CharacterLookSearch.type = 'all'; getCharacterLookList();" />
        <el-dialog v-model="initModelDialogVisible" class="generate-storyboard-dialog" draggable>
            <template #header>
                <span class="font-weight-600">初始化装扮</span>
            </template>
            <xl-models v-model="initCurrentCharacterLook.model_id" scene="character_look_costume" no-init />
            <template #footer>
                <div class="flex flex-center grid-gap-2">
                    <el-button type="info" @click="initModelDialogVisible = false"
                        :disabled="initLoading">取消</el-button>
                    <el-button type="success" icon="Check" @click="handleCharacterLookInitSubmit"
                        :disabled="!initCurrentCharacterLook.model_id || initLoading"
                        :loading="initLoading">初始化</el-button>
                </div>
            </template>
        </el-dialog>
    </div>
</template>
<style lang="scss" scoped>
.character-look-item {
    cursor: pointer;

    &-image {
        --el-avatar-border-radius: 8px;
        width: 100%;
        height: 137px;
        border-style: solid;
        border-width: 2px;
        border-color: transparent;
    }

    &-active {
        .character-look-item-image {
            border-color: var(--el-color-success);
        }
    }
}

.input-upload {
    width: 300px;

    :deep(.el-upload) {
        --el-fill-color-blank: var(--el-bg-color-overlay);
        --el-color-primary: var(--el-border-color-hover);
        --el-upload-dragger-padding-horizontal: 0;
        --el-upload-dragger-padding-vertical: 0;

        .el-upload-dragger {
            border: none;
            min-height: 300px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 6px;
        }
    }

    .image-cover {
        width: 300px;
        height: 300px;
    }
}

.input-button {
    background-color: var(--el-fill-color-darker);
    cursor: pointer;

    &:hover {
        background-color: var(--el-fill-color-dark);
    }
}

.icon-model {
    font-size: 20px;
    width: 22px;
    height: 22px;
}
</style>