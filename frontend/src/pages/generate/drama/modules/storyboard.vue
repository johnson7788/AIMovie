<script lang="ts" setup>
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { ElMessage, ElMessageBox } from 'element-plus';
const props = withDefaults(defineProps<{
    modelValue: string | number
    storyboard: any[]
    scene: any[]
    currentSceneId?: string | number
    drama_id: string | number
    episode_id: string | number
    episodeInfo: any
}>(), {
    modelValue: '',
    storyboard: () => [],
    scene: () => [],
    currentSceneId: undefined,
    drama_id: '',
    episode_id: '',
    episodeInfo: () => ({}),
});
const emit = defineEmits(['update:modelValue', 'update:storyboard', 'update:currentSceneId']);
const episodeInfo = ref(props.episodeInfo);
watch(() => props.episodeInfo, (newVal) => {
    episodeInfo.value = newVal;
});
const storyboardList = ref<any[]>(props.storyboard);
watch(() => props.storyboard, (newVal) => {
    storyboardList.value = newVal;
});
watch(storyboardList, (newVal) => {
    emit('update:storyboard', newVal);
});
const currentStoryboardId = ref(props.modelValue);
watch(currentStoryboardId, (newVal) => {
    emit('update:modelValue', newVal);
});
const currentSceneId = ref(props.currentSceneId);
watch(currentSceneId, (newVal) => {
    emit('update:currentSceneId', newVal);
});
const handleChangeStoryboardLoading = ref(false);
const handleChangeStoryboard = (row: any, newSort?: number) => {
    if (newSort === undefined) return;
    handleChangeStoryboardLoading.value = true;
    // 拿到全部数据
    const list = storyboardList.value;
    const originalList = JSON.parse(JSON.stringify(storyboardList.value));

    // 只拿当前场景的
    const currentStoryboardList = list
        .sort((a, b) => a.sort - b.sort);

    // 找到当前操作的 item 在 currentStoryboardList 里的 index
    const oldIndex = currentStoryboardList.findIndex(i => i.id === row.id);
    if (oldIndex === -1) return;

    // 目标 index
    const newIndex = currentStoryboardList.findIndex(i => i.sort === newSort);
    if (newIndex === -1) return;

    // 移动元素
    const current = currentStoryboardList.splice(oldIndex, 1)[0];
    currentStoryboardList.splice(newIndex, 0, current);

    // 重新编号 sort（只改当前场景的 sort）
    currentStoryboardList.forEach((item, index) => {
        item.sort = index + 1;
    });
    // 替换回 storyboardList
    storyboardList.value = list.map(item => {
        const found = currentStoryboardList.find(i => i.id === item.id);
        return found ?? item; // 当前场景更新，其他场景保持不动
    });
    $http.post('/app/shortplay/api/Storyboard/updateSort', {
        drama_id: props.drama_id,
        episode_id: props.episode_id,
        storyboards: currentStoryboardList.map((item: any) => {
            return {
                id: item.id,
                sort: item.sort,
            }
        }),
    })
        .then((res: any) => {
            if (res.code !== ResponseCode.SUCCESS) {
                ElMessage.error(res.msg);
                storyboardList.value = originalList;
            }
        }).catch(() => {
            ElMessage.error('更新分镜失败');
            storyboardList.value = originalList;
        }).finally(() => {
            handleChangeStoryboardLoading.value = false;
        });
};
const handleCopyStoryboardLoading = ref(false);

const handleCopyStoryboard = (row: any) => {
    handleCopyStoryboardLoading.value = true;
    const originalList = storyboardList.value;

    // 当前场景的列表（深拷贝避免引用问题）
    const sceneList = originalList
        .map(item => ({ ...item }))
        .sort((a, b) => a.sort - b.sort);

    // 找当前 row 在场景中的位置
    const index = sceneList.findIndex(i => i.id === row.id);
    if (index === -1) {
        handleCopyStoryboardLoading.value = false;
        return;
    }

    // ❗创建复制项（注意要删除 id，由后端生成）
    const copiedItem = {
        ...row,
        id: undefined,
        sort: row.sort + 1
    };

    // 插入到当前项后面
    sceneList.splice(index + 1, 0, copiedItem);

    // 重新编号 sort（保证顺序连续）
    sceneList.forEach((item, idx) => {
        item.sort = idx + 1;
    });

    // 复制前的备份（用于失败回滚）
    const backup = JSON.parse(JSON.stringify(originalList));

    // ✨ 乐观更新 UI
    storyboardList.value = originalList.map(item => {
        const found = sceneList.find(i => i.id === item.id);
        return found ?? item;
    });

    // ❗注意：copiedItem.id 是 undefined，因此要把新增的项也插入到原数组
    storyboardList.value.push(copiedItem);

    // 请求服务端：新增分镜
    $http.post('/app/shortplay/api/Storyboard/copyStoryboard', {
        drama_id: props.drama_id,
        episode_id: props.episode_id,
        copy_id: row.id,
        new_sort: copiedItem.sort
    })
        .then((res: any) => {
            if (res.code === ResponseCode.SUCCESS) {
                // 服务端会返回新生成的 id
                copiedItem.id = res.data.id;

                // 替换 UI 中该项的 id
                storyboardList.value = storyboardList.value.map(item => {
                    if (item === copiedItem && !item.id) {
                        return { ...item, id: res.data.id };
                    }
                    return item;
                });

                ElMessage.success('复制成功');
            } else {
                ElMessage.error(res.msg);
                storyboardList.value = backup; // 回滚
            }
        })
        .catch(() => {
            ElMessage.error('复制失败');
            storyboardList.value = backup; // 回滚
        })
        .finally(() => {
            handleCopyStoryboardLoading.value = false;
        });
};
const handleDeleteStoryboardLoading = ref(false);

const handleDeleteStoryboard = (row: any) => {
    handleDeleteStoryboardLoading.value = true;

    const sceneId = row.scene_id;

    // 🔥 删除前备份（用于失败回滚）
    const backup = JSON.parse(JSON.stringify(storyboardList.value));

    // 当前场景原数据
    const list = storyboardList.value;

    // ✨ 1. 乐观更新 UI —— 先删掉
    const newList = list.filter(item => item.id !== row.id);

    // ✨ 2. 只对当前场景的 sort 重新排序
    const sortedSceneList = newList
        .sort((a, b) => a.sort - b.sort)
        .map((item, index) => ({
            ...item,
            sort: index + 1
        }));

    // 合并回原数组
    storyboardList.value = newList.map(item => {
        const hit = sortedSceneList.find(i => i.id === item.id);
        return hit ?? item;
    });

    // 🔥 3. 调用服务端删除接口
    $http.post('/app/shortplay/api/Storyboard/deleteStoryboard', {
        id: row.id,
        scene_id: sceneId,
        drama_id: props.drama_id,
        episode_id: props.episode_id,
    })
        .then((res: any) => {
            if (res.code === ResponseCode.SUCCESS) {
                ElMessage.success('删除成功');
            } else {
                ElMessage.error(res.msg);

                // ❗服务端失败 → 回滚 UI
                storyboardList.value = backup;
            }
        })
        .catch(() => {
            ElMessage.error('删除失败');

            // ❗请求失败 → 回滚
            storyboardList.value = backup;
        })
        .finally(() => {
            handleDeleteStoryboardLoading.value = false;
        });
};

const actorButtonRef = ref();
const handleInsertEmptyStoryboard = (afterItem?: any) => {
    $http.post('/app/shortplay/api/Storyboard/insertAfter', {
        drama_id: props.drama_id,
        episode_id: props.episode_id,
        after_id: afterItem?.id
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            const newId = res.data.id
            let sort = 1;
            const itemData = {
                id: newId,
                scene_id: null,
                drama_id: props.drama_id,
                sort: sort,
                component: "form",
                description: '',
                dialogue: null
            };
            if (afterItem) {
                // 插入本地
                const index = storyboardList.value.findIndex(item => item.id === afterItem.id)
                itemData.sort = afterItem.sort + 1;
                sort = itemData.sort;
                storyboardList.value.splice(index + 1, 0, itemData)
            } else {
                storyboardList.value.push(itemData)
            }
            storyboardList.value.sort((a, b) => a.sort - b.sort).forEach((item) => {
                if (item.sort >= sort && item.id !== newId) {
                    item.sort++;
                }
            })

        } else {
            ElMessage.error(res.msg)
        }
    }).catch(() => {
        ElMessage.error('插入失败')
    })
}
const handleMouseEnterStoryboard = (item: any) => {
    if (item.editMode || item.saveLoading) return
    item.component = 'form'
    // 深拷贝原始数据，用于取消
    item.originData = JSON.parse(JSON.stringify(item))
}
const handleCancel = (item: any) => {
    const origin = item.originData
    if (origin) {
        Object.assign(item, origin)
    }

    item.originData = null
    item.editMode = false
    item.component = 'view'
}
const handleSave = (item: any) => {
    if (!item.editMode) return
    item.saveLoading = true
    $http.post('/app/shortplay/api/Storyboard/update', item).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            item.originData = null;
            handleCancel(item);
            item.sceneFind = props.scene.find(scene => scene.id === item.scene_id);
            currentSceneId.value = item.scene_id
        } else {
            ElMessage.error(res.msg)
        }
    }).catch(() => {
        ElMessage.error('保存失败')
    }).finally(() => {
        item.saveLoading = false
    })
}
const initLoading = ref<any>(false);
const initForm = reactive({
    model_id: '',
});
const generateStoryboardDialogVisible = ref(false);

const handleGenerateStoryboardCancel = () => {
    generateStoryboardDialogVisible.value = false;
}
const handleGenerateStoryboard = () => {
    if (initLoading.value) return;
    initLoading.value = true;
    $http.post('/app/shortplay/api/Generate/storyboard', {
        ...initForm,
        drama_id: props.drama_id,
        episode_id: props.episode_id,
    }).then((res: any) => {
        initLoading.value = false;
        if (res.code === ResponseCode.SUCCESS) {
            episodeInfo.value.init_storyboard_state = true;
            generateStoryboardDialogVisible.value = false;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        initLoading.value = false;
        ElMessage.error('绘制分镜失败');
    }).finally(() => {
        initLoading.value = false;
    });
}
const handleDeleteDialogue = (index: number, dialogueIndex: number) => {
    const dialogue = storyboardList.value[index].dialogues[dialogueIndex];
    ElMessageBox.confirm('确定删除该对话吗？', '提示', {
        title: '提示',
        message: '确定删除该对话吗？',
        beforeClose: (action: any, instance: any, done: () => void) => {
            if (action === 'confirm') {
                instance.confirmButtonLoading = true;
                instance.cancelButtonLoading = true;
                $http.post('/app/shortplay/api/StoryboardDialogue/delete', {
                    drama_id: props.drama_id,
                    storyboard_id: storyboardList.value[index].id,
                    dialogue_id: dialogue.id,
                }).then((res: any) => {
                    if (res.code === ResponseCode.SUCCESS) {
                        ElMessage.success('删除成功');
                        storyboardList.value[index].dialogues.splice(dialogueIndex, 1)
                        done();
                    } else {
                        ElMessage.error(res.msg);
                    }
                }).catch(() => {
                    ElMessage.error('删除失败');
                }).finally(() => {
                    instance.confirmButtonLoading = false;
                    instance.cancelButtonLoading = false;
                });
            } else {
                done();
            }
        }
    })
}
const dialogueCreateRef = ref<any>();
const handleAddDialogue = (item: any) => {
    dialogueCreateRef.value?.open(item);
}
const handleEditDialogue = (item: any, dialogue: any) => {
    dialogueCreateRef.value?.open(item, dialogue);
}
const handleDialogueCreateSuccess = (item: any, dialogue: any) => {
    const find=item.dialogues.find((d:any)=>d.id===dialogue.id)
    if (find) {
        Object.assign(find, dialogue);
    } else {
        item.dialogues.push(dialogue);
    }
}
defineExpose({
    openCreateStoryboard: handleInsertEmptyStoryboard,
    openGenerateStoryboard: () => {
        generateStoryboardDialogVisible.value = true
    }
})
</script>
<template>
    <el-scrollbar class="storyboard-scrollbar p-4" ref="storyboardScrollbarRef"
        v-loading="handleCopyStoryboardLoading || handleDeleteStoryboardLoading">
        <div class="storyboard-list pb-10">
            <el-empty v-if="storyboardList.length === 0" description="暂无分镜">
                <!-- <el-button type="success" @click="generateStoryboardDialogVisible = true">AI绘制</el-button> -->
                <el-button type="success" icon="Plus" bg text @click="handleInsertEmptyStoryboard()"
                    v-if="props.scene.length">新增</el-button>
            </el-empty>
            <div class="p-6 bg-gray rounded-4 flex flex-column grid-gap-4 storyboard-item"
                :class="{ 'storyboard-item-current': item.id === currentStoryboardId }"
                v-for="(item, index) in storyboardList" :key="item.id"
                @click="currentStoryboardId = item.id; currentSceneId = item.scene_id">
                <div class="flex grid-gap-4 flex-center">
                    <el-input-number :model-value="item.sort" :min="1" :controls="false"
                        :disabled="handleChangeStoryboardLoading" style="width: 120px;font-weight: 600;" size="large"
                        @change="($event: any) => handleChangeStoryboard(item, $event)">
                        <template #prefix>
                            <span class="text-dark h10">分镜</span>
                        </template>
                    </el-input-number>
                    <div class="flex-1"></div>
                    <div class="flex flex-center grid-gap-2 storyboard-item-copy"
                        @click="handleAddDialogue(item)">
                        <el-icon size="16" class="text-info">
                            <ChatDotRound />
                        </el-icon>
                        <span>新增对话</span>
                    </div>
                    <div class="flex flex-center grid-gap-2 storyboard-item-copy"
                        @click="handleMouseEnterStoryboard(item)">
                        <el-icon size="16">
                            <Edit />
                        </el-icon>
                        <span>编辑</span>
                    </div>
                    <div class="flex flex-center grid-gap-2 storyboard-item-copy"
                        @click.stop="handleCopyStoryboard(item)">
                        <el-icon size="16">
                            <CopyDocument />
                        </el-icon>
                        <span>复制</span>
                    </div>
                    <el-popconfirm icon="Delete" title="确定删除该分镜吗？" placement="bottom-end" confirm-button-type="danger"
                        width="fit-content" @confirm="handleDeleteStoryboard(item)">
                        <template #reference>
                            <div class="flex flex-center grid-gap-2 storyboard-item-delete">
                                <el-icon size="16">
                                    <Delete />
                                </el-icon>
                                <span>删除</span>
                            </div>
                        </template>
                    </el-popconfirm>
                </div>
                <el-button type="success" icon="Plus" class="storyboard-item-add"
                    @click="handleInsertEmptyStoryboard(item)"></el-button>
                <div class=" flex flex-column grid-gap-4" v-if="item.component === 'view'">
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">场景：</span>
                        <div class="flex-1">
                            <span class="text-regular" v-if="item.sceneFind">
                                {{ item.sceneFind.title }}·{{ item.sceneFind.scene_location }}
                            </span>
                        </div>
                    </div>
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">镜头设计：</span>
                        <div class="flex-1 flex grid-gap-2">
                            <span class="el-tag el-tag--info text-wrap" v-if="item.shot_type">{{ item.shot_type
                            }}</span>
                            <span class="el-tag el-tag--info text-wrap" v-if="item.shot_angle">{{ item.shot_angle
                            }}</span>
                            <span class="el-tag el-tag--info text-wrap" v-if="item.shot_motion">{{ item.shot_motion
                            }}</span>
                        </div>
                    </div>
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">出镜演员：</span>
                        <div class="flex-1 flex grid-gap-2">
                            <span class="el-tag el-tag--info text-wrap" v-for="actor in item.actors" :key="actor.id">
                                {{ actor.actor.name }}
                            </span>
                        </div>
                    </div>
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">时长：</span>
                        <div class="flex-1">
                            <span class="text-info">{{ item.duration / 1000 }}秒</span>
                        </div>
                    </div>
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">画面描述：</span>
                        <div class="flex-1">
                            <span class="text-info">{{ item.description }}</span>
                        </div>
                    </div>
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">首帧图提示词：</span>
                        <div class="flex-1">
                            <span class="text-info">{{ item.image_prompt }}</span>
                        </div>
                    </div>
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">视频提示词：</span>
                        <div class="flex-1">
                            <span class="text-info">{{ item.video_prompt }}</span>
                        </div>
                    </div>
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">音效：</span>
                        <div class="flex-1">
                            <span class="text-info">{{ item.sfx }}</span>
                        </div>
                    </div>
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">旁白内容：</span>
                        <div class="flex-1">
                            <span class="text-info">{{ item.narration }}</span>
                        </div>
                    </div>
                    <div class="flex">
                        <span class="storyboard-item-label pt-5">对话内容：</span>
                        <div class="flex-1 flex flex-column grid-gap-2 flex-y-flex-start"
                            v-if="item.dialogues?.length > 0">
                            <div class="flex grid-gap-2 el-tag el-tag--success flex-column "
                                v-for="(dialogue, dialogueIndex) in item.dialogues" :key="dialogue.id">
                                <span class="text-wrap pointer" @click="handleEditDialogue(item,dialogue)"> {{ dialogue.actor.name }}{{ dialogue.inner_monologue?'(内心OS)':'' }}:{{ dialogue.content }} </span>
                                <div class="h10 text-info flex grid-gap-4">
                                    <span>语速：{{ dialogue.prosody_speed }}x</span>
                                    <span>音量：{{ dialogue.prosody_volume }}</span>
                                    <span>情感：{{ dialogue.emotion }}</span>
                                    <span>字幕时长：{{ dialogue.start_time / 1000 }} ~ {{ dialogue.end_time / 1000 }}秒</span>
                                </div>
                                <el-icon class="dialogue-delete-icon"
                                    @click.stop="handleDeleteDialogue(index, dialogueIndex as number)">
                                    <Close />
                                </el-icon>
                            </div>
                        </div>
                        <div class="flex-1" v-else></div>
                    </div>
                </div>
                <el-form v-else-if="item.component === 'form'" class=" flex flex-column grid-gap-4" size="large"
                    :disabled="item.saveLoading">
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">场景：</span>
                        <div class="flex-1">
                            <el-select v-model="item.scene_id" :teleported="false"
                                style=" --el-select-bg-color: var(--el-bg-color); --el-select-input-focus-border-color: var(--el-color-success);"
                                placeholder="选择场景" @change="item.editMode = true">
                                <el-option v-for="scene in props.scene" :key="scene.id"
                                    :label="scene.title + '·' + scene.scene_location" :value="scene.id">
                                    {{ scene.title }}·{{ scene.scene_location }}
                                </el-option>
                            </el-select>
                        </div>
                    </div>
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">镜头设计：</span>
                        <div class="flex-1 flex grid-gap-2 flex-x-flex-start">
                            <el-select class="storyboard-item-select" v-model="item.shot_type" filterable allow-create
                                :teleported="false" placeholder="镜头类型" @change="item.editMode = true">
                                <el-option label="远景镜头" value="远景镜头" />
                                <el-option label="中景镜头" value="中景镜头" />
                                <el-option label="近景镜头" value="近景镜头" />
                                <el-option label="特写镜头" value="特写镜头" />
                            </el-select>
                            <el-select class="storyboard-item-select" v-model="item.shot_angle" filterable allow-create
                                :teleported="false" placeholder="镜头视角" @change="item.editMode = true">
                                <el-option label="正面镜头" value="正面镜头" />
                                <el-option label="侧面镜头" value="侧面镜头" />
                                <el-option label="背面镜头" value="背面镜头" />
                                <el-option label="斜侧面镜头" value="斜侧面镜头" />
                                <el-option label="斜背面镜头" value="斜背面镜头" />
                                <el-option label="斜正面镜头" value="斜正面镜头" />
                                <el-option label="斜侧面背面镜头" value="斜侧面背面镜头" />
                                <el-option label="斜侧面正面镜头" value="斜侧面正面镜头" />
                                <el-option label="斜背面正面镜头" value="斜背面正面镜头" />
                            </el-select>
                            <el-select class="storyboard-item-select" v-model="item.shot_motion" filterable allow-create
                                :teleported="false" placeholder="镜头运动" @change="item.editMode = true">
                                <el-option label="固定镜头" value="固定镜头" />
                                <el-option label="平稳推进" value="平稳推进" />
                                <el-option label="缓慢推进" value="缓慢推进" />
                                <el-option label="快速推进" value="快速推进" />
                                <el-option label="极速推进" value="极速推进" />
                                <el-option label="缓慢后退" value="缓慢后退" />
                                <el-option label="快速后退" value="快速后退" />
                            </el-select>
                        </div>
                    </div>
                    <div class="flex flex-center">
                        <span class="storyboard-item-label">出镜演员：</span>
                        <div class="flex-1 flex grid-gap-2">
                            <span class="el-tag el-tag--info text-wrap" v-for="actor in item.actors" :key="actor.id"
                                closable>
                                <span class="el-tag__content">{{ actor.actor.name }}</span>
                                <el-icon class="el-tag__close" @click.stop="">
                                    <Close />
                                </el-icon>
                            </span>
                        </div>
                    </div>
                    <div class="flex grid-gap-2">
                        <span class="storyboard-item-label pt-3">画面描述：</span>
                        <el-input v-model="item.description" type="textarea" :autosize="{ minRows: 1, maxRows: 10 }"
                            placeholder="请输入画面描述" class="storyboard-item-textarea" @input="item.editMode = true" />
                    </div>
                    <div class="flex grid-gap-2">
                        <span class="storyboard-item-label pt-3">首帧图提示词：</span>
                        <el-input v-model="item.image_prompt" type="textarea" :autosize="{ minRows: 1, maxRows: 10 }"
                            placeholder="请输入首帧图提示词" class="storyboard-item-textarea" @input="item.editMode = true" />
                    </div>
                    <div class="flex grid-gap-2">
                        <span class="storyboard-item-label pt-3">视频提示词：</span>
                        <el-input v-model="item.video_prompt" type="textarea" :autosize="{ minRows: 1, maxRows: 10 }"
                            placeholder="请输入视频提示词" class="storyboard-item-textarea" @input="item.editMode = true" />
                    </div>
                    <div class="flex grid-gap-2">
                        <span class="storyboard-item-label pt-3">音效：</span>
                        <el-input v-model="item.sfx" type="textarea" :autosize="{ minRows: 1, maxRows: 10 }"
                            placeholder="请输入音效" class="storyboard-item-textarea" @input="item.editMode = true" />
                    </div>
                    <div class="flex grid-gap-2">
                        <span class="storyboard-item-label pt-3">旁白内容：</span>
                        <el-input v-model="item.narration" type="textarea" :autosize="{ minRows: 1, maxRows: 10 }"
                            placeholder="请输入旁白内容" class="storyboard-item-textarea" @input="item.editMode = true" />
                    </div>
                    <div class="flex flex-x-flex-end">
                        <el-button type="info" @click.stop="handleCancel(item)">取消</el-button>
                        <el-button type="success" icon="Check" @click.stop="handleSave(item)" :disabled="!item.editMode"
                            :loading="item.saveLoading">保存</el-button>
                    </div>
                </el-form>
            </div>
        </div>
        <div class="loading-mask" v-if="episodeInfo.init_storyboard_state" v-loading="episodeInfo.init_storyboard_state"
            element-loading-text="绘制分镜中..."></div>
        <el-popover :virtual-ref="actorButtonRef" virtual-triggering placement="bottom-start" width="min(100vw,880px)"
            trigger="click">
            <xl-actor />
        </el-popover>
        <el-dialog v-model="generateStoryboardDialogVisible" class="generate-storyboard-dialog" draggable>
            <template #header>
                <span class="font-weight-600">AI绘制分镜</span>
            </template>
            <el-alert title="当前分集尚未创建分镜，是否使用AI绘制？" type="warning" :closable="false" />
            <xl-models v-model="initForm.model_id" scene="creative_storyboards" no-init />
            <template #footer>
                <div class="flex flex-center grid-gap-2">
                    <el-button type="info" @click="handleGenerateStoryboardCancel"
                        :disabled="initLoading">取消</el-button>
                    <el-button type="success" icon="Check" @click="handleGenerateStoryboard"
                        :disabled="!initForm.model_id || initLoading" :loading="initLoading">绘制</el-button>
                </div>
            </template>
        </el-dialog>
        <xl-dialogue-create ref="dialogueCreateRef" @success="handleDialogueCreateSuccess" />
    </el-scrollbar>
</template>
<style lang="scss" scoped>
.storyboard-scrollbar {

    .loading-mask {
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        right: 0;
        z-index: 1;
    }

}

.storyboard-list {
    display: flex;
    flex-direction: column;
    height: fit-content;
    gap: 30px;

    .storyboard-item:last-child {
        margin-bottom: 50px;
    }

    .storyboard-item {
        position: relative;

        &-current {
            box-shadow: inset 0 0 0 2px var(--el-color-success);
        }

        .storyboard-item-add {
            position: absolute;
            top: calc(100% - 10px);
            left: 50%;
            transform: translateX(-50%);
            z-index: 1;
            height: 50px;
            width: 50px;
            font-size: 20px;
        }

        &-copy,
        &-delete {
            display: none;
            cursor: pointer;
            color: var(--el-text-color-secondary);

            &:hover {
                color: var(--el-text-color-primary);
            }
        }

        &:hover {

            .storyboard-item-copy,
            .storyboard-item-delete {
                display: flex;
            }
        }

        &-delete:hover {
            color: var(--el-color-danger);
        }

        &-delete-confirm {
            :deep(.el-popper) {
                width: fit-content;
                background: var(--el-bg-color-page);
                border: 1px solid var(--el-border-color);
                border-radius: 6px;
            }
        }
    }

    .storyboard-item-label {
        width: 100px;
        text-align: right;
        color: var(--el-text-color-primary);
    }

    .icon-actor {
        width: 20px;
        height: 20px;
    }

    .storyboard-item-textarea {
        width: calc(100% - 100px);
        --el-input-bg-color: var(--el-bg-color);
        --el-input-border-color: var(--el-bg-color);
        --el-input-border-radius: 6px;
        --el-input-focus-border-color: var(--el-bg-color);
        --el-input-text-color: var(--el-text-color-primary);
        --el-input-placeholder-color: var(--el-text-color-placeholder);
        --el-input-focus-text-color: var(--el-text-color-primary);
        --el-input-focus-placeholder-color: var(--el-text-color-placeholder);
        --el-input-focus-border-color: var(--el-bg-color);
        --el-input-hover-border-color: var(--el-bg-color);

        :deep(.el-textarea__inner) {
            resize: none;
            padding: 10px;
        }
    }

    .dialogue-item-input {
        --el-input-bg-color: var(--el-bg-color);
        --el-input-border-color: var(--el-bg-color);
        --el-input-border-radius: 6px;
        --el-input-focus-border-color: var(--el-bg-color);
        --el-input-text-color: var(--el-text-color-primary);
        --el-input-placeholder-color: var(--el-text-color-placeholder);
        --el-input-focus-text-color: var(--el-text-color-primary);
        --el-input-focus-placeholder-color: var(--el-text-color-placeholder);
        --el-input-focus-border-color: var(--el-bg-color);
        --el-input-hover-border-color: var(--el-bg-color);
    }

    .el-tag {
        white-space: wrap;
        height: auto;
        min-height: 32px;
        line-height: 1.5;
        padding: 8px 10px;
        justify-content: flex-start;
        align-items: flex-start;
        position: relative;

        &:hover {
            .dialogue-delete-icon {
                display: flex;
            }
        }
    }

    .dialogue-delete-icon {
        position: absolute;
        top: -5px;
        left: -10px;
        width: 20px;
        height: 20px;
        background-color: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(6px);
        color: var(--el-color-info);
        border-radius: 50%;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        display: none;

        &:hover {
            background-color: rgba(0, 0, 0, 0.8);
        }
    }
}

.storyboard-item-select {
    width: 180px;
    --el-select-bg-color: var(--el-bg-color);
    --el-select-input-focus-border-color: var(--el-color-success);
}
</style>