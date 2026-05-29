<template>
    <div class="container">
        <el-scrollbar height="100%" wrap-class="flex-1" @end-reached="scrollBarEndReached" v-if="columns.length > 0">
            <div ref="containerRef" class="waterfall">
                <div class="column" v-for="(col, colIndex) in columns" :key="colIndex">
                    <div class="item" v-for="item in col.list" :key="item.id" @click="handleItemClick(item)">
                        <img :src="item.drama.cover" />
                        <span class="h10 font-weight-600 episode_num">共 {{ item.episode_num }} 集</span>
                        <div
                            class="flex p-4 flex-y-center grid-gap-2 flex-x-space-between position-absolute bottom-0 left-0 right-0">
                            <div class="flex flex-y-center grid-gap-2">
                                <el-avatar :src="item.user.headimg" :alt="item.user.nickname" :size="24" />
                                <span class="h9">{{ item.user.nickname }}</span>
                            </div>
                            <div class="flex flex-y-center grid-gap-2 pointer"
                                :class="[item.is_likes ? 'text-danger' : 'text-info']" @click.stop="handleLike(item)">
                                <el-icon :size="16">
                                    <IconLike />
                                </el-icon>
                                <span class="h9">{{ item.likes }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </el-scrollbar>
        <div class="flex flex-center" v-else>
            <el-empty description="暂无数据" />
        </div>
    </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import IconLike from '@/svg/icon/icon-like.vue'
import { $http } from '@/common/http'
import { ResponseCode } from '@/common/const'
import router from '@/routers'
import { useUserStore } from '@/stores'

/* ================== 常量 ================== */
const COLUMN_COUNT = 4
const GAP = 16

/* ================== 类型 ================== */
interface Column {
    height: number
    list: any[]
}

/* ================== 状态 ================== */
const containerRef = ref<HTMLDivElement | null>(null)

const columns = ref<Column[]>(
    Array.from({ length: COLUMN_COUNT }, () => ({
        height: 0,
        list: [],
    }))
)

const searchForm = reactive({
    page: 1,
    page_size: 10,
})

const loading = ref(false)
const finished = ref(false)

/* ================== 工具函数 ================== */
function loadImage(src: string, colWidth: number): Promise<number> {
    return new Promise((resolve, reject) => {
        const img = new Image()
        img.onload = () => {
            resolve((img.height * colWidth) / img.width)
        }
        img.onerror = reject
        img.src = src
    })
}

function getMinColumnIndex(): number {
    let minIndex = 0
    let minHeight = columns.value[0].height

    for (let i = 1; i < columns.value.length; i++) {
        if (columns.value[i].height < minHeight) {
            minHeight = columns.value[i].height
            minIndex = i
        }
    }
    return minIndex
}

function appendItem(item: any) {
    const index = getMinColumnIndex()
    const col = columns.value[index]

    col.list.push(item)
    col.height += item.height + GAP
}

/* ================== 数据初始化 ================== */
async function init(data: any[]) {
    if (!containerRef.value || !data.length) return

    const containerWidth = containerRef.value.clientWidth
    const colWidth =
        (containerWidth - GAP * (COLUMN_COUNT - 1)) / COLUMN_COUNT

    const tasks = data
        .filter(item => item?.drama?.cover)
        .map(async item => {
            try {
                const height = await loadImage(item.drama.cover, colWidth)
                return { ...item, height } as any
            } catch {
                return null
            }
        })

    const results = await Promise.allSettled(tasks)

    results.forEach(res => {
        if (res.status === 'fulfilled' && res.value) {
            appendItem(res.value)
        }
    })
}

/* ================== 请求 ================== */
async function getList() {
    if (loading.value || finished.value) return

    loading.value = true
    try {
        const res: any = await $http.get(
            '/app/shortplay/api/Square/index',
            { params: searchForm }
        )

        const list = res?.data?.data || []

        if (res.code === ResponseCode.SUCCESS && list.length) {
            await init(list)
        } else {
            finished.value = true
        }
    } catch (e) {
        console.error('获取列表失败:', e)
    } finally {
        loading.value = false
    }
}

function scrollBarEndReached() {
    if (finished.value) return
    searchForm.page++
    getList()
}

function handleItemClick(item: any) {
    router.push(`/play/${item.drama_id}/${item.episode.episode_id}`)
}
const userStore = useUserStore();
const handleLike = (item: any) => {
    if (!userStore.hasLogin()) return;
    $http.post('/app/shortplay/api/Square/likes', {
        drama_id: item.drama_id,
        episode_id: item.episode_id
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            item.is_likes = !item.is_likes;
            item.likes = res.data.likes;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('点赞失败');
    })
}
onMounted(getList)
</script>

<style scoped lang="scss">
.container {
    width: 100%;
    height: calc(100dvh - var(--xl-header-height));
    padding: 20px 150px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.waterfall {
    display: flex;
    gap: 1px;
    min-width: 700px;
}

.column {
    flex: 1;
}

.item {
    margin-bottom: 1px;
    position: relative;
    background-color: var(--el-bg-color-page);
    overflow: hidden;
    cursor: pointer;

    .episode_num {
        position: absolute;
        top: 10px;
        left: 10px;
        color: #FFFFFF;
        background-color: rgba(0, 0, 0, 0.15);
        padding: 4px 8px;
        border-radius: 4px;
        backdrop-filter: blur(10px);
    }
}

.item img {
    width: 100%;
    display: block;
    border-radius: 8px;
    transition: transform 0.3s ease;

    &:hover {
        transform: scale(1.05);
    }
}
</style>