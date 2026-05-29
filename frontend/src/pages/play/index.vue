<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import router from '@/routers';
import IconLike from '@/svg/icon/icon-like.vue'
import { useUserStore } from '@/stores';
import { Action, ElMessageBox, MessageBoxState } from 'element-plus';
import { LocationQueryValue, useRoute } from 'vue-router';
const route = useRoute();
const drama_id = ref<string>(route.params.drama_id as string);
const episode_id = ref<string>(route.params.episode_id as string);
const showView = ref<LocationQueryValue | LocationQueryValue[]>(route.query.view)
const userStore = useUserStore();
const episodeDetails = ref<any>({
    video_path: '',
    drama: {}
});
watch(() => route.path, () => {
    drama_id.value = route.params.drama_id as string;
    episode_id.value = route.params.episode_id as string;
    if (showView.value) {
        getEpisode();
    } else {
        getShare();
    }
});
const getEpisode = () => {
    if (!userStore.hasLogin()) return;
    $http.get('/app/shortplay/api/DramaEpisode/details', {
        params: {
            drama_id: drama_id.value,
            episode_id: episode_id.value
        }
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            episodeDetails.value = res.data;
        } else {
            ElMessageBox.confirm(res.msg, '提示', {
                confirmButtonText: '重新加载',
                cancelButtonText: '返回',
                type: 'warning',
            }).then(() => {
                getEpisode();
            }).catch(() => {
                router.push('/works/' + drama_id.value);
            });
        }
    }).catch(() => {
        ElMessageBox.confirm('加载失败，请重新加载', '提示', {
            confirmButtonText: '重新加载',
            cancelButtonText: '返回',
            type: 'warning',
        }).then(() => {
            getEpisode();
        }).catch(() => {
            router.push('/works/' + drama_id.value);
        });
    })
}
const handleShare = () => {
    ElMessageBox.confirm('发布到广场后，其他用户可以查看并点赞，是否继续？', '提示', {
        confirmButtonText: '继续发布',
        cancelButtonText: '取消',
        type: 'warning',
        beforeClose: (action: Action, instance: MessageBoxState, done: () => void) => {
            if (instance.confirmButtonLoading == true) return;
            if (action === 'confirm') {
                instance.confirmButtonLoading = true;
                $http.post('/app/shortplay/api/DramaEpisode/share', {
                    drama_id: drama_id.value,
                    episode_id: episode_id.value
                }).then((res: any) => {
                    if (res.code === ResponseCode.SUCCESS) {
                        ElMessage.success('发布成功');
                        getEpisode();
                        done();
                    } else {
                        ElMessage.error(res.msg);
                    }
                }).catch(() => {
                    ElMessage.error('发布失败');
                }).finally(() => {
                    instance.confirmButtonLoading = false;
                });
            } else {
                done();
            }
        }
    }).then(() => {
        console.log('handleShare');
    }).catch(() => {
        console.log('handleShare');
    });
}
const getShare = () => {
    episodeDetails.value.video_path = '';
    $http.get('/app/shortplay/api/Square/details', {
        params: {
            drama_id: drama_id.value,
            episode_id: episode_id.value
        }
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            episodeDetails.value = res.data;
        } else {
            ElMessageBox.confirm(res.msg, '提示', {
                confirmButtonText: '重新加载',
                cancelButtonText: '返回',
                type: 'warning',
            }).then(() => {
                getEpisode();
            }).catch(() => {
                router.push('/works/' + drama_id.value);
            });
        }
    }).catch(() => {
        ElMessageBox.confirm('加载失败，请重新加载', '提示', {
            confirmButtonText: '重新加载',
            cancelButtonText: '返回',
            type: 'warning',
        }).then(() => {
            getEpisode();
        }).catch(() => {
            router.push('/works/' + drama_id.value);
        });
    })
}
const shareEpisodes = ref<any>({});
const getShareEpisode = () => {
    $http.get('/app/shortplay/api/Square/episodes', {
        params: {
            drama_id: drama_id.value
        }
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            shareEpisodes.value = res.data;
        }
    }).catch(() => {
    })
}
const handleLike = () => {
    if (!userStore.hasLogin()) return;
    $http.post('/app/shortplay/api/Square/likes', {
        drama_id: drama_id.value,
        episode_id: episode_id.value
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            episodeDetails.value.share.is_likes = !episodeDetails.value.share.is_likes;
            episodeDetails.value.share.likes = res.data.likes;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('点赞失败');
    })
}
onMounted(() => {
    if (showView.value) {
        getEpisode();
    } else {
        getShare();
        getShareEpisode();
    }
})  
</script>
<template>
    <div class="play-container flex grid-gap-10">
        <div class="flex-1 flex grid-gap-4">
            <div class="flex-1 h-100 flex flex-center">
                <video :src="episodeDetails.video_path" controls class="play-video"
                    v-if="episodeDetails.video_path"></video>
            </div>
            <div class="flex flex-column grid-gap-10 flex-y-flex-end">
                <el-icon class="pointer" @click="router.back()" size="30">
                    <Close />
                </el-icon>
                <el-scrollbar class="flex-1">
                    <div class="flex flex-column grid-gap-4" style="width: 100px;">
                        <div class="p-4 rounded-4 flex flex-center pointer" v-for="(item, index) in shareEpisodes"
                            :key="index"
                            :class="[item.episode_id === episode_id ? 'bg-success text-white' : 'bg-overlay']"
                            @click="router.replace('/play/' + drama_id + '/' + item.episode_id)">
                            <span class="font-weight-600">第 {{ item.episode_no }} 集</span>
                        </div>
                    </div>
                </el-scrollbar>
            </div>
        </div>
        <div class="drama-info bg-overlay rounded-4 flex flex-column grid-gap-4">
            <div class="flex grid-gap-2 flex-center mb-10" v-if="!showView && episodeDetails.user">
                <el-avatar :src="episodeDetails.user.headimg" :size="40"></el-avatar>
                <div class="flex-1 flex flex-column grid-gap-2">
                    <span>{{ episodeDetails.user.nickname }}</span>
                    <span class="h10 text-info">{{ episodeDetails.share.create_time }}</span>
                </div>
                <div class="flex flex-center grid-gap-2 pointer"
                    :class="[episodeDetails.is_likes ? 'text-danger' : 'text-info']" @click="handleLike">
                    <el-icon size="16">
                        <IconLike />
                    </el-icon>
                    <span class="h10">{{ episodeDetails.share.likes }}</span>
                </div>
            </div>
            <span class="font-weight-600">{{ episodeDetails.drama.title }}</span>
            <div class="flex flex-column grid-gap-2">
                <span>作品描述</span>
                <span class="text-info">{{ episodeDetails.drama.description }}</span>
            </div>
            <div class="flex-1"></div>
            <template v-if="showView === 'share'">
                <el-button type="success" icon="Position" size="large" disabled
                    v-if="episodeDetails.is_share">已发布到广场</el-button>
                <el-button type="success" icon="Position" size="large" v-else @click="handleShare">发布到广场</el-button>
            </template>
        </div>
    </div>
</template>
<style scoped lang="scss">
.play-container {
    height: calc(100vh - var(--xl-header-height));
    overflow: hidden;
    padding: 20px;

    .play-video {
        width: min(100%, 1280px);
        margin: 0 auto;
        height: min(100%, 720px);
        object-fit: contain;
        object-position: center;
    }

    .drama-info {
        width: 400px;
        height: 100%;
        padding: 20px;
    }
}
</style>