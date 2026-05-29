<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useWebConfigStore, useUserStore, useRefs } from '@/stores';
import { UploadFilled } from '@element-plus/icons-vue';
import { usePush } from '@/composables/usePush';
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
const ActorSearch = reactive({
    type: 'personal',
    name: '',
    actor_id: '',
    species_type: null,
    gender: null,
    age: null
})
const actorList = ref<any[]>([]);
const loading = ref(false);
const actorCreateRef = ref<any>(null);
const getActorList = () => {
    loading.value = true;
    $http.get('/app/shortplay/api/Actor/index', { params: ActorSearch }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            actorList.value = res.data;
        }
    }).catch((error) => {
        console.error('getActorList error', error);
    }).finally(() => {
        loading.value = false;
    })
}
const handleDeleteActor = (item: any) => {
    $http.post('/app/shortplay/api/Actor/delete', {
        id: item.id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            getActorList();
        } else {
            ElMessage.error(res.msg);
        }
    })
}
const previewImageVisible = ref(false);
const imageList = ref<any[]>([]);
const { subscribe, unsubscribeAll } = usePush();
const addListener = () => {
    subscribe('private-generateactorimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = actorList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            findItem.status_enum = res.status;
            if (res.image) {
                findItem.headimg = res.image;
            }
        }
        actorCreateRef.value?.subscribe?.('generateactorimage', res);
    });
    subscribe('private-generateactorthreeviewimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = actorList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            findItem.status_enum = res.status;
            if (res.image) {
                findItem.three_view_image = res.image;
            }
        }
        actorCreateRef.value?.subscribe?.('generateactorthreeviewimage', res);
    });
}
onMounted(() => {
    getActorList();
    addListener();
})
onUnmounted(() => {
    console.log('actors unmounted');
    unsubscribeAll();
})
</script>
<template>
    <div class="flex flex-column draw-module grid-gap-4">
        <el-form class="flex flex-center grid-gap-4" @submit.prevent="getActorList">
            <el-form-item class="mb-0">
                <el-input v-model="ActorSearch.name" placeholder="搜索演员" clearable @change="getActorList">
                    <template #suffix>
                        <el-icon>
                            <Search />
                        </el-icon>
                    </template>
                </el-input>
            </el-form-item>
            <div class="flex-1"></div>
            <el-form-item class="mb-0" style="width: 80px;">
                <el-select v-model="ActorSearch.species_type" placeholder="物种" clearable :teleported="false"
                    @change="getActorList">
                    <el-option v-for="item in WEBCONFIG?.enum?.actor_species_type" :key="item.value" :label="item.label"
                        :value="item.value" />
                </el-select>
            </el-form-item>
            <el-form-item class="mb-0" style="width: 80px;">
                <el-select v-model="ActorSearch.gender" placeholder="性别" clearable :teleported="false"
                    @change="getActorList">
                    <el-option v-for="item in WEBCONFIG?.enum?.actor_gender" :key="item.value" :label="item.label"
                        :value="item.value" />
                </el-select>
            </el-form-item>
            <el-form-item class="mb-0" style="width: 80px;">
                <el-select v-model="ActorSearch.age" placeholder="年龄" clearable :teleported="false"
                    @change="getActorList">
                    <el-option v-for="item in WEBCONFIG?.enum?.actor_age" :key="item.value" :label="item.label"
                        :value="item.value" />
                </el-select>
            </el-form-item>
        </el-form>
        <el-scrollbar class="flex-1">
            <div
                class="grid-columns-xxl-7 grid-columns-xl-6 grid-columns-lg-5 grid-columns-md-4 grid-columns-sm-3 grid-columns-xs-2 grid-columns-p-1 grid-gap-4">
                <div class="grid-column-1 rounded-4 p-4 actor-item flex flex-column flex-center grid-gap-4 pointer bg-overlay"
                    @click="actorCreateRef?.open?.(null)">
                    <el-icon class="rounded-4" size="20"
                        style="height: 40px; width: 40px;background-color: var(--el-fill-color-dark);">
                        <Plus />
                    </el-icon>
                    <span>添加演员</span>
                </div>
                <div class="grid-column-1 input-button rounded-4 flex flex-column flex-center grid-gap-2 actor-item bg-overlay border"
                    v-for="item in actorList" :key="item.id">
                    <el-avatar :src="item.headimg" class="actor-avatar bg-mosaic" fit="cover"
                        :title="item.is_edit ? item.name : '公共角色不可编辑'">
                        {{ item.name }}
                    </el-avatar>
                    <div class="actor-edit-mask flex flex-column grid-gap-4 flex-center pointer"
                        @click="actorCreateRef?.open?.(item)">
                        <div class="flex flex-center bg-overlay rounded-round p-2 pointer grid-gap-2"
                            @click.stop="actorCreateRef?.upload?.(item)">
                            <el-icon size="16">
                                <UploadFilled />
                            </el-icon>
                            <span class="h10">手动上传</span>
                        </div>
                        <el-popconfirm title="确定删除该演员吗？" width="fit-content" @confirm="handleDeleteActor(item)"
                            placement="bottom-end">
                            <template #reference>
                                <div class="flex flex-center bg-overlay rounded-round p-2 pointer grid-gap-2"
                                    @click.stop>
                                    <el-icon size="16">
                                        <Delete />
                                    </el-icon>
                                    <span class="h10">删除演员</span>
                                </div>
                            </template>
                        </el-popconfirm>
                    </div>
                    <div class="flex grid-gap-2 actor-status">
                        <!-- <span class="actor-tag pointer" title="复制演员"
                                    @click.stop="setClipboard(`@${item.name}(${item.actor_id}) `)">{{
                                        item.actor_id
                                    }}</span> -->
                        <div class="flex-1"></div>
                        <div class="flex flex-column flex-y-flex-end grid-gap-2">
                            <span class="actor-tag" :class="[`actor-tag--` + item.status_enum.props.type]">
                                {{ item.status_enum.label }}
                            </span>
                        </div>
                    </div>
                    <div class="flex flex-column grid-gap-2 actor-info">
                        <div class="actor-name flex flex-center grid-gap-1 pointer"
                            @click.stop="actorCreateRef?.open?.(item)">
                            <el-icon size="16">
                                <UserFilled />
                            </el-icon>
                            <span>{{ item.name }}</span>
                        </div>
                        <!-- <div class="flex grid-gap-2">
                                    <span class="actor-tag">{{ item.species_type_enum?.label
                                        }}</span>
                                    <span class="actor-tag">{{ item.gender_enum?.label }}</span>
                                    <span class="actor-tag">{{ item.age_enum?.label }}</span>
                                </div> -->
                    </div>
                </div>
            </div>
        </el-scrollbar>
        <el-image-viewer :url-list="imageList" v-if="previewImageVisible" @close="previewImageVisible = false" />
        <xl-actor-create ref="actorCreateRef" @success="getActorList" />
    </div>
</template>
<style lang="scss" scoped>
.draw-module {
    flex: 1;
    padding: 20px;
    overflow: hidden;

    .actor-form-wrapper {
        width: 450px;
        height: 100%;
        overflow: hidden;
    }

    .actor-item {
        height: 260px;
        position: relative;
        overflow: hidden;
        box-shadow: inset 0 0 0px 2px transparent;

        &:hover {
            background-color: var(--el-fill-color-dark);

            .actor-delete {
                opacity: 1;
            }
        }

        &.active {
            box-shadow: inset 0 0 0px 2px var(--el-color-success);
        }

        .actor-avatar {
            height: 260px;
            width: 100%;
            border-radius: 0px;
        }

        .bg-overlay {
            background-color: rgba(0, 0, 0, 0.5);
        }

        .actor-edit-mask {
            position: absolute;
            top: 0;
            left: 0;
            height: 260px;
            width: 100%;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;

            &:hover {
                opacity: 1;
            }
        }

        .actor-status {
            position: absolute;
            top: 0;
            right: 0;
            width: 100%;
            padding: 10px;
            justify-content: flex-start;
            align-items: flex-start;
            z-index: 1;
        }

        .actor-info {
            position: absolute;
            bottom: 0px;
            left: 0;
            width: 100%;
            padding: 10px;
            justify-content: flex-start;
            align-items: flex-start;
            z-index: 1;
        }


        .actor-tag,
        .actor-name {
            background-color: rgba(0, 0, 0, 0.25);
            backdrop-filter: blur(10px);
            color: #FFFFFF;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;

            &--primary {
                color: var(--el-color-primary);
            }

            &--success {
                color: var(--el-color-success);
            }

            &--warning {
                color: var(--el-color-warning);
            }

            &--danger {
                color: var(--el-color-danger);
            }

            &--info {
                color: var(--el-color-info);
            }

            &.pointer:hover {
                background-color: rgba(0, 0, 0, 0.5);
            }
        }

        .actor-delete {
            width: 28px;
            height: 28px;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }


        .actor-name {
            padding: 4px 8px;
            border-radius: 20px;
        }

        .actor-action {
            height: 50px;
            width: 100%;
        }
    }

    .actor-form {
        &-input {
            :deep(.el-input__wrapper) {
                box-shadow: none;
            }
        }

        &-select {
            :deep(.el-select__wrapper) {
                background-color: var(--el-bg-color);
            }
        }

        &-textarea {
            :deep(.el-textarea__inner) {
                box-shadow: none;
                padding: 0;
                resize: none;
            }
        }
    }

    .task-item {
        position: relative;

        .task-item-replace {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: rgba(0, 0, 0, 0.5);
            padding: 5px 10px;
            border-radius: 99px;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }

        &:hover {
            .task-item-replace {
                opacity: 1;
            }
        }
    }
}
</style>