<script setup lang="ts">
import { ResponseCode } from '@/common/const'
import { debounce, fileSizeToStr } from '@/common/functions'
import { $http } from '@/common/http'
import { useLogin } from '@/composables/useLogin'
import router from '@/routers'
import { useRefs, useUserStore, useStateStore } from '@/stores'
import { ElMessage, type MentionOption } from 'element-plus'
import UploadSvg from '@/svg/icon/upload.vue'
import IconStyleSvg from '@/svg/icon/icon-style.vue'
import IconModelSvg from '@/svg/icon/icon-model.vue'
import IconAtSvg from '@/svg/icon/icon-at.vue';
import IconUploadImageSvg from '@/svg/icon/icon-upload-image.vue';
import { usePush } from '@/composables/usePush'
import ScriptSvg from '@/svg/icon/video-file.vue'
import DramaSvg from '@/svg/icon/drama.vue'
import { useLoading } from '@/composables/useLoading'

const userStore = useUserStore()
const { USERINFO } = useRefs(userStore);
watch(USERINFO, () => {
	addListener();
});
const stateStore = useStateStore()
const login = useLogin()
const form = reactive({
	model: '',
	script: 'drama',
	title: '',
	cover: '',
	description: '',
	import: '',
	prompt: '',
	style: '',
	aspect_ratio: '9:16',
	episode_sum: 20,
	episode_duration: 60
})

interface ExamplePreset {
	label: string
	mode: 'script' | 'drama'
	prompt: string
	style: string
	aspect_ratio: string
	episode_sum: number
	episode_duration: number
	model_id: string
}

const examplePresets: ExamplePreset[] = [
	{
		label: '橘猫探访书店',
		mode: 'script',
		prompt: 'A curious orange tabby cat explores a cozy old bookshop filled with towering shelves and warm golden lamplight. The cat leaps between stacked books, knocks over a pile, and chases a dust mote caught in a sunbeam. Between adventures, it curls up on an open novel by the window and purrs contentedly.',
		style: 'storybook',
		aspect_ratio: '9:16',
		episode_sum: 3,
		episode_duration: 60,
		model_id: '',
	},
	{
		label: '蝴蝶的第一次飞翔',
		mode: 'script',
		prompt: 'A newly emerged orange-striped butterfly takes its first flight in a spring garden. It accidentally picks up pollen while brushing flower buds, pauses on a kitten\'s paw, and touches an old grandma\'s half-finished butterfly embroidery. Finally it delivers carried pollen to a waiting rose, which unfurls all its petals.',
		style: 'storybook',
		aspect_ratio: '9:16',
		episode_sum: 4,
		episode_duration: 60,
		model_id: '',
	},
	{
		label: '赛博朋克侦探',
		mode: 'script',
		prompt: 'In a neon-lit cyberpunk city, a hard-boiled detective investigates a series of AI malfunctions. Rain-slicked streets reflect holographic ads as the detective follows digital breadcrumbs through underground hacker dens and corporate towers.',
		style: 'cinematic',
		aspect_ratio: '9:16',
		episode_sum: 5,
		episode_duration: 60,
		model_id: '',
	},
	{
		label: '都市爱情故事',
		mode: 'drama',
		prompt: '两个年轻人在繁忙的都市中偶然相遇，从误解到理解，从陌生到熟悉。在追逐梦想的路上，他们互相扶持，共同成长，一段温暖治愈的都市爱情故事徐徐展开。',
		style: 'cinematic',
		aspect_ratio: '9:16',
		episode_sum: 20,
		episode_duration: 60,
		model_id: '',
	},
	{
		label: '古装武侠传奇',
		mode: 'drama',
		prompt: '少年侠客初入江湖，意外卷入一场惊天阴谋。在刀光剑影中磨砺成长，在恩怨情仇中坚守本心。江湖路远，儿女情长，一段荡气回肠的武侠传奇就此展开。',
		style: 'anime',
		aspect_ratio: '9:16',
		episode_sum: 40,
		episode_duration: 60,
		model_id: '',
	},
]

const options = ref<MentionOption[]>([])
const loading = ref(false)
const mentionRef = ref();
let controller: AbortController | null = null;
let searchLoading = false;
const sendSearch = debounce((pattern: string, prefix: string) => {
	loading.value = true
	if (controller) {
		controller.abort();
	}
	let url = '/app/shortplay/api/Actor/index';
	if (prefix === '#') {
		url = '/app/shortplay/api/Prop/index';
	}
	controller = new AbortController();
	$http.get(url, { params: { name: pattern, limit: 100 }, signal: controller.signal }).then((res: any) => {
		if (res.code === ResponseCode.SUCCESS) {
			nextTick(() => {
				options.value = res.data.map((item: any) => ({
					...item,
					view: prefix === '@' ? 'actor' : 'prop',
					label: `${item.name}{${prefix === '@' ? item.actor_id : item.prop_id}}`,
					value: `${item.name}{${prefix === '@' ? item.actor_id : item.prop_id}}`,
				}))
			})
		}
	}).catch(() => {
	}).finally(() => {
		loading.value = false
		controller = null;
	})
}, 300);
const handleSearch = (pattern: string, prefix: string) => {
	searchLoading = true;
	sendSearch(pattern, prefix);
}
const mentionPrefix = ['@', '#'];
const handleKeyDown = (e: KeyboardEvent | Event) => {
	if (e instanceof KeyboardEvent) {
		if (!e.shiftKey && e.code === 'Enter' && !searchLoading) {
			e.preventDefault();
			e.stopPropagation();
			if (form.script === 'script') {
				submit();
			} else {
				showDramaCreateDialog();
			}
		} else if (!e.shiftKey && e.code === 'Enter' && searchLoading) {
			e.preventDefault();
			e.stopPropagation();
		} else if (e.code === 'Space' || e.code === 'Escape') {
			searchLoading = false;
		}
	}
}
const handleSelect = () => {
	searchLoading = false;
}
const checkIsWhole = (pattern: string) => {
	searchLoading = false;
	return pattern.trim().split('\n').length === 1;
}
const { subscribe, unsubscribeAll } = usePush();
let uuids: string[] = [];
const addListener = () => {
	if (userStore.hasLogin()) {
		subscribe('private-clonevoice-' + USERINFO.value?.user, (res: any) => {
			if (uuids.includes(res.id)) {
				xlLoading.close();
				if (res.drama_id) {
					ElMessage.success(res.msg);
					router.push('/works/' + res.drama_id)
				} else {
					ElMessage.error(res.msg);
				}
			}
		});
	}
}
const xlLoading = useLoading({
	title: '剧本创作中，预计3-5分钟~',
	tips: '退出页面，剧本会继续生成',
	auto: true,
	list: [
		{
			title: '解析剧本中...',
			start: 0,
			end: 20,
			progress: 20
		},
		{
			title: '正在创作剧本卖点...',
			start: 20,
			end: 25,
			progress: 10,
		},
		{
			title: '正在创作剧本爽点...',
			start: 25,
			end: 30,
			progress: 10,
		},
		{
			title: '正在创作剧本主线...',
			start: 30,
			end: 35,
			progress: 10,
		},
		{
			title: '正在创作剧本关系...',
			start: 35,
			end: 40,
			progress: 10,
		},
		{
			title: '正在创作剧本描述...',
			start: 40,
			end: 45,
			progress: 10,
		},
		{
			title: '正在创作剧本背景...',
			start: 45,
			end: 50,
			progress: 10,
		},
		{
			title: '正在创作剧本大纲...',
			start: 50,
			end: 9999,
			progress: 20,
		},
	],
	showCancelButton: true,
	showConfirmButton: true,
	cancelButtonText: '返回首页',
	confirmButtonText: '去作品广场',
	confirmButtonClick: () => {
		xlLoading.close();
		router.push('/square');
	},
	cancelButtonClick: () => {
		xlLoading.close();
	}
});
const resetForm = () => {
	form.model = '';
	form.script = 'script';
	form.title = '';
	form.cover = '';
	form.description = '';
	form.import = '';
	form.prompt = '';
	form.style = '';
	form.aspect_ratio = '9:16';
	form.episode_sum = 20;
	form.episode_duration = 60;
	styleFind.value = { id: '' };
	selectedModel.value = { id: '' };
}
const submit = () => {
	if (!userStore.hasLogin()) {
		return login.open()
	}
	if (loading.value) {
		return;
	}
	loading.value = true;
	$http.post('app/shortplay/api/Index/submit', {
		...form,
	}).then((res: any) => {
		if (res.code === ResponseCode.SUCCESS) {
			resetForm();
			if (res.data.drama_id) {
				router.push('/works/' + res.data.drama_id)
			} else {
				xlLoading.open();
				uuids.push(res.data.uuid);
			}
		} else {
			ElMessage.error(res.msg);
		}
	}).catch(() => {
		ElMessage.error('提交失败');
	}).finally(() => {
		loading.value = false;
	});
}
const showDramaCreateDialog = () => {
	if (!userStore.hasLogin()) {
		return login.open();
	}
	if (!form.style) {
		ElMessage.error('请选择风格');
		return;
	}
	dramaCreateDialogVisible.value = true;
}
const actorButtonRef = ref();
const actorPopoverRef = ref();
const styleButtonRef = ref();
const stylePopoverRef = ref();
const handleActorSelect = (item: any) => {
	form.prompt += ` @${item.name}{${item.actor_id}} `;
	actorPopoverRef.value?.hide();
	nextTick(() => {
		mentionRef.value?.input?.ref?.focus()
	});
}
const styleFind = ref<any>({ id: '' })
const handleStyleSelect = (item: any) => {
	styleFind.value = item;
	stylePopoverRef.value?.hide();
}
const uploadRef = ref();
const uploadCoverRef = ref();
const beforeUpload = () => {
	if (!userStore.hasLogin()) {
		uploadRef.value?.clearFiles();
		uploadCoverRef.value?.clearFiles();
		login.open()
		return false;
	}
	return true;
}
const uploadSuccess = ref<any>({})
const uploadCoverSuccess = ref<any>({})
const handleUploadSuccess = (response: any) => {
	if (response.code === ResponseCode.SUCCESS) {
		switch (response.data.dir_name) {
			case 'drama/cover':
				form.cover = response.data.url;
				uploadCoverSuccess.value = response.data;
				uploadCoverRef.value?.clearFiles();
				break;
			case 'drama/content':
				form.import = response.data.url;
				uploadSuccess.value = response.data;
				uploadRef.value?.clearFiles();
				break;
		}
	} else {
		ElMessage.error(response.msg);
	}
}
const handleUploadError = () => {
	uploadRef.value?.clearFiles();
	uploadCoverRef.value?.clearFiles();
}
const dramaCreateDialogVisible = ref(false);
const dramaUploadDialogVisible = ref(false);
const modelButtonRef = ref();
const modelPopoverRef = ref();
const selectedModel = ref<any>({});
const handleModelSelect = (item: any) => {
	selectedModel.value = item;
	// form.model = item.id;
	modelPopoverRef.value?.hide();
}
const handleScriptChange = (val: any) => {
	switch (val) {
		case 'script':
			form.episode_sum = 3;
			break;
		case 'drama':
			form.episode_sum = 80;
			break;
	}
}
const applyExample = (example: ExamplePreset) => {
	form.script = example.mode;
	form.prompt = example.prompt;
	form.style = example.style;
	form.aspect_ratio = example.aspect_ratio;
	form.episode_sum = example.episode_sum;
	form.episode_duration = example.episode_duration;
	form.model = example.model_id;
	styleFind.value = { id: example.style };
	selectedModel.value = { id: '' };
	nextTick(() => {
		mentionRef.value?.input?.ref?.focus();
	});
}
onMounted(() => {
	addListener();
})
onUnmounted(() => {
	unsubscribeAll();
})
</script>

<template>
	<div class="flex flex-column  flex-center px-10 page-layouts grid-gap-6">
		<span class="head-title">一句话生成一部短剧</span>
		<span class="head-subtitle">剧本、分镜、画面、配音、剪辑，一站式智能生成</span>
		<el-segmented v-model="form.script" :disabled="loading"
			:options="[{ label: '剧本模式', value: 'drama', icon: DramaSvg }, { label: '创意模式', value: 'script', icon: ScriptSvg }]"
			class="tabs-segmented border" @change="handleScriptChange">
			<template #default="{ item }">
				<div class="flex flex-center grid-gap-2">
					<el-icon size="20">
						<component :is="item.icon" />
					</el-icon>
					<span>{{ item.label }}</span>
				</div>
			</template>
		</el-segmented>
		<div class="input-box" v-loading="loading">
			<div class="rounded-4 p-4 input-bg">
				<el-mention ref="mentionRef" v-model="form.prompt" :autosize="{ minRows: 6, maxRows: 50 }"
					popper-class="prompt-popper" type="textarea" :prefix="mentionPrefix"
					placeholder="请输入剧本创作提示词，@演员名称可以引用演员，#物品名称可以引用物品，Shift + Enter换行，Enter提交" :options="options"
					:loading="loading" whole :check-is-whole="checkIsWhole" @search="handleSearch"
					@keydown="handleKeyDown" @select="handleSelect"
					@focus="stateStore.setState('InputFocusState', true)"
					@blur="stateStore.setState('InputFocusState', false)">
					<template #label="{ item }">
						<template v-if="item.view === 'actor'">
							<el-avatar :src="item.headimg" :alt="item.label" :size="30" />
							<div class="flex-1 flex flex-column">
								<span>{{ item.label }}</span>
								<span class="text-secondary h10">{{ item.species_type_enum?.label }}·{{
									item.gender_enum?.label }}·{{ item.age_enum?.label }}</span>
							</div>
						</template>
						<template v-else-if="item.view === 'prop'">
							<el-avatar :src="item.image" :alt="item.label" :size="30" />
							<div class="flex-1 flex flex-column">
								<span>{{ item.label }}</span>
							</div>
						</template>
					</template>
				</el-mention>
				<div class="flex grid-gap-4 flex-center mt-4">
					<!-- <div class="flex flex-center input-button  p-3" @click="dramaUploadDialogVisible = true">
						<el-icon size="20" color="var(--el-color-white)">
							<Plus />
						</el-icon>
					</div> -->
					<div class="flex flex-center input-button  p-3" ref="modelButtonRef">
						<template v-if="!form.model">
							<el-icon size="20" color="var(--el-color-white)">
								<IconModelSvg />
							</el-icon>
						</template>
						<template v-else>
							<div class="flex flex-center grid-gap-1">
								<el-avatar :src="selectedModel.icon" :alt="selectedModel.name" shape="circle"
									class="icon-model"></el-avatar>
								<span class="h10 text-ellipsis-1">{{ selectedModel.name }}</span>
								<el-icon size="16" color="var(--el-text-color-secondary)"
									class="model-item-selected-icon font-weight-600"
									@click.stop="form.model = ''; selectedModel = { id: '' }">
									<Close />
								</el-icon>
							</div>
						</template>
					</div>
					<div class="flex flex-center input-button  p-3" ref="actorButtonRef">
						<el-icon size="20" color="var(--el-color-white)">
							<IconAtSvg />
						</el-icon>
					</div>
					<div class="flex flex-center input-button  p-3" ref="styleButtonRef">
						<template v-if="!styleFind.id">
							<el-icon size="20" color="var(--el-color-white)">
								<IconStyleSvg />
							</el-icon>
						</template>
						<template v-else>
							<div class="flex flex-center grid-gap-1">
								<el-avatar :src="styleFind.image" :alt="styleFind.name" shape="circle"
									class="icon-style"></el-avatar>
								<span class="h10 text-ellipsis-1">{{ styleFind.name }}</span>
								<el-icon size="16" color="var(--el-text-color-secondary)"
									class="model-item-selected-icon font-weight-600"
									@click.stop="styleFind.id = ''; styleFind = { id: '' }">
									<Close />
								</el-icon>
							</div>
						</template>
					</div>

					<xl-aspect-ratio v-model="form.aspect_ratio" />
					<xl-episode-sum v-model="form.episode_sum" :allow-input="form.script === 'script'" />
					<xl-episode-duration v-if="form.script !== 'script'" v-model="form.episode_duration" />
					<div class="flex-1"></div>
					<div class="flex flex-center grid-gap-2 input-button " style="width: 40px; height: 40px;"
						@click="submit">
						<el-icon size="20">
							<Loading v-if="loading" class="circular" />
							<Top v-else />
						</el-icon>
					</div>
				</div>
			</div>
		</div>
		<div class="example-presets">
			<span class="example-presets-label">示例：</span>
			<span
				v-for="example in examplePresets"
				:key="example.label"
				class="example-preset-chip"
				:class="{ 'is-drama': example.mode === 'drama' }"
				@click="applyExample(example)"
			>
				{{ example.label }}
			</span>
		</div>
		<!-- <div class="input-box " v-if="form.script === 'drama'" v-loading="loading">
			<div class="rounded-4 p-4 ">
				<el-input type="textarea" v-model="form.description"
					@focus="stateStore.setState('InputFocusState', true)"
					@blur="stateStore.setState('InputFocusState', false)" :autosize="{ minRows:6, maxRows: 30 }"
					class="input-textarea" maxlength="200" show-word-limit placeholder="输入短剧描述..."
					@keydown="handleKeyDown" />
				<div class="flex grid-gap-2 flex-y-center py-4" v-show="showUpload">
					<span>或者</span>
					<el-icon color="var(--el-color-success)">
						<UploadSvg />
					</el-icon>
					<span class="text-success h10 pointer" @click="dramaUploadDialogVisible = true">点击上传剧本</span>
				</div>
				<div class="flex grid-gap-4 flex-center mt-4">
					<div class="flex flex-center input-button  p-3"  @click="dramaUploadDialogVisible = true">
						<el-icon size="20" color="var(--el-color-white)">
							<Plus />
						</el-icon>
					</div>
					<div class="flex flex-center input-button  p-3" ref="modelButtonRef">
						<template v-if="!form.model">
							<el-icon size="20" color="var(--el-color-white)">
								<IconModelSvg />
							</el-icon>
						</template>
						<template v-else>
							<div class="flex flex-center grid-gap-1">
								<el-avatar :src="selectedModel.icon" :alt="selectedModel.name" shape="circle"
									class="icon-model"></el-avatar>
								<span class="h10 text-ellipsis-1">{{ selectedModel.name }}</span>
								<el-icon size="16" color="var(--el-text-color-secondary)"
									class="model-item-selected-icon font-weight-600"
									@click.stop="form.model = ''; selectedModel = { id: '' }">
									<Close />
								</el-icon>
							</div>
						</template>
					</div>

					<div class="flex flex-center grid-gap-2 input-button  py-2 px-6" ref="styleButtonRef">
						<template v-if="!styleFind.id">
							<el-icon alt="风格" class="icon-style">
								<IconStyleSvg />
							</el-icon>
							<span class="h10">风格</span>
						</template>
						<template v-else>
							<el-avatar :src="styleFind.image" :alt="styleFind.name" class="icon-style"></el-avatar>
							<span class="h10">{{ styleFind.name }}</span>
							<el-icon size="20" class="pointer" @click.stop="styleFind.id = ''; styleFind = { id: '' }">
								<Close />
							</el-icon>
						</template>
					</div>
					<div class="flex flex-center input-button  p-3" ref="styleButtonRef">
						<template v-if="!styleFind.id">
							<el-icon size="20" color="var(--el-color-white)">
								<IconStyleSvg />
							</el-icon>
						</template>
						<template v-else>
							<div class="flex flex-center grid-gap-1">
								<el-avatar :src="styleFind.image" :alt="styleFind.name" shape="circle"
									class="icon-style"></el-avatar>
								<span class="h10 text-ellipsis-1">{{ styleFind.name }}</span>
								<el-icon size="16" color="var(--el-text-color-secondary)"
									class="model-item-selected-icon font-weight-600"
									@click.stop="styleFind.id = ''; styleFind = { id: '' }">
									<Close />
								</el-icon>
							</div>
						</template>
					</div>
					<xl-aspect-ratio v-model="form.aspect_ratio" />
					<xl-episode-sum v-model="form.episode_sum" />
					<xl-episode-duration v-model="form.episode_duration" />
					<div class="flex-1"></div>
					<div class="flex flex-center grid-gap-2 input-button " style="width: 40px; height: 40px;"
						@click="showDramaCreateDialog">
						<el-icon size="20">
							<Loading v-if="loading" class="circular" />
							<Top v-else />
						</el-icon>
					</div>
				</div>
			</div>
		</div> -->
		<el-popover ref="actorPopoverRef" :show-arrow="false" popper-class="model-popover" :virtual-ref="actorButtonRef"
			virtual-triggering placement="bottom-start" width="min(100vw,880px)" trigger="click">
			<xl-actor @select="handleActorSelect" />
		</el-popover>
		<el-popover ref="stylePopoverRef" :show-arrow="false" popper-class="model-popover" :virtual-ref="styleButtonRef"
			virtual-triggering placement="bottom-start" width="min(100vw,640px)" trigger="click">
			<xl-style v-model="form.style" @select="handleStyleSelect" />
		</el-popover>
		<el-popover ref="modelPopoverRef" :show-arrow="false" popper-class="model-popover" :virtual-ref="modelButtonRef"
			virtual-triggering placement="bottom" width="min(100vw,380px)" trigger="click">
			<xl-models v-model="form.model" @select="handleModelSelect" scene="creative_script" />
		</el-popover>




		<el-dialog v-model="dramaCreateDialogVisible" class="drama-dialog" draggable>
			<template #header>
				<span class="font-weight-600">为短剧命名</span>
			</template>
			<span class="h10">剧本名称</span>
			<el-input v-model="form.title" placeholder="请输入剧本标题" size="large" class="input-title" />
			<span class="h10">剧本封面</span>
			<el-upload ref="uploadCoverRef" class="input-upload flex-1" drag
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
			<template #footer>
				<el-button type="info" @click="dramaCreateDialogVisible = false" size="large" color="#F9F9F9"><span
						class="text-bg">取消</span></el-button>
				<el-button type="success" @click="submit" size="large">提交</el-button>
			</template>
		</el-dialog>
		<el-dialog v-model="dramaUploadDialogVisible" class="drama-dialog" draggable>
			<template #header>
				<span class="font-weight-600">导入本地文件</span>
			</template>
			<el-upload ref="uploadRef" class="input-upload flex-1" drag
				:data="{ dir_name: 'drama/content', dir_title: '剧本' }"
				:action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')" :before-upload="beforeUpload"
				:headers="$http.getHeaders()" accept=".docx,.txt,.excel" :limit="1" :on-success="handleUploadSuccess"
				:show-file-list="false" :on-error="handleUploadError">
				<el-icon class="el-icon--upload" v-if="!uploadSuccess.url" color="var(--el-color-success)">
					<UploadSvg />
				</el-icon>
				<template v-else>
					<div class="flex flex-column flex-center grid-gap-2 py-6 bg mb-4 rounded-4">
						<span class="h1">{{ uploadSuccess.filename }}</span>
						<el-tag type="info">{{ fileSizeToStr(uploadSuccess.size) }}</el-tag>
					</div>
				</template>
				<div class="el-upload__text">
					<span class="h10 text-success">拖拽文件到此处或点击上传</span>
				</div>
				<div class="el-upload__text">
					<span class="h10">支持上传格式：</span>
					<span class="h10">DOCX, TXT,EXCEL</span>
				</div>
				<div class="el-upload__text">
					<span class="h10">限制说明：</span>
					<span class="h10">单个文件不超过 10MB 或 20页（以先达到者为准）</span>
				</div>
			</el-upload>
			<template #footer>
				<el-button type="info" @click="dramaUploadDialogVisible = false" size="large" color="#F9F9F9"><span
						class="text-bg">取消</span></el-button>
				<el-button type="success" @click="submit" size="large">提交</el-button>
			</template>
		</el-dialog>
	</div>
</template>

<style scoped lang="scss">
.page-layouts {
	position: relative;
	min-height: calc(100vh - var(--xl-header-height));
	z-index: 2;
}

.head-title {
	font-weight: 900;
	font-size: 55px;
	line-height: 55px;
	text-align: center;
	font-style: normal;
	text-transform: none;
	color: transparent;
	background-clip: text;
	-webkit-background-clip: text;
	-webkit-text-fill-color: transparent;
	background-image: linear-gradient(to left, #79FFFF 0%, #0DF283 100%);
	// margin-top: calc(300px - var(--xl-header-height) - 30px);
}

.head-subtitle {
	text-align: center;
	font-style: normal;
	text-transform: none;
	color: transparent;
	background-clip: text;
	-webkit-background-clip: text;
	-webkit-text-fill-color: transparent;
	background-image: linear-gradient(to right, var(--el-text-color-secondary), #FFFFFF, var(--el-text-color-secondary));
}


.input-box {
	width: 100%;
	max-width: 1000px;
	padding: 2px;
	// background-image: linear-gradient(90deg, rgba(120, 255, 255, 1), rgba(13, 242, 131, 1));
	background: rgba(0, 0, 0, 0.04);
	border-radius: 20px;
	border: 0px solid rgba(0, 0, 0, 0.15);
	backdrop-filter: blur(8px);
	-webkit-backdrop-filter: blur(10px);
	// margin-top: 10px;
	margin-bottom: 350px;

	.el-mention {
		--el-input-border: none;

		:deep(.el-textarea__inner) {
			box-shadow: none;
			padding: 0;
			resize: none;
		}
	}

	.input-textarea {
		--el-input-border: none;

		:deep(.el-textarea__inner) {
			box-shadow: none;
			padding: 0;
			resize: none;
		}
	}
}

.input-title.el-input {
	--el-input-border: none;
	--el-input-bg-color: var(--el-bg-color-overlay);

	:deep(.el-input__wrapper) {
		box-shadow: none;
	}
}

.input-upload {
	:deep(.el-upload) {
		--el-fill-color-blank: var(--el-bg-color-overlay);
		--el-color-primary: var(--el-border-color-hover);
		--el-upload-dragger-padding-horizontal: 0;
		--el-upload-dragger-padding-vertical: 0;

		.el-upload-dragger {
			border: none;
			min-height: 260px;
			display: flex;
			flex-direction: column;
			justify-content: center;
			align-items: center;
			gap: 6px;
		}
	}

	.image-cover {
		width: 400px;
		height: 300px;
	}
}

.input-button {
	background: rgba(0, 0, 0, 0.06);
	cursor: pointer;
	border-radius: 20px;

	&:hover {
		background: rgba(0, 0, 0, 0.1);
	}
}

.icon-actor,
.icon-style,
.icon-model {
	font-size: 20px;
	width: 20px;
	height: 20px;
	flex-shrink: 0;

}

.actor-item {
	height: 80px;
	cursor: pointer;
	border-width: 2px;
	border-color: var(--el-fill-color-darker);

	&:hover {
		background-color: var(--el-fill-color-dark);
	}
}

.example-presets {
	width: 100%;
	max-width: 1000px;
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;

	&-label {
		font-size: 12px;
		color: var(--el-text-color-secondary);
		white-space: nowrap;
	}

	&-chip {
		font-size: 12px;
		padding: 4px 12px;
		border-radius: 12px;
		cursor: pointer;
		background: rgba(255, 255, 255, 0.06);
		border: 1px solid rgba(255, 255, 255, 0.1);
		color: var(--el-text-color-regular);
		white-space: nowrap;
		transition: all 0.2s;

		&:hover {
			background: rgba(13, 242, 131, 0.12);
			border-color: rgba(13, 242, 131, 0.3);
			color: #0DF283;
		}

		&.is-drama {
			background: rgba(121, 255, 255, 0.06);
			border-color: rgba(121, 255, 255, 0.1);

			&:hover {
				background: rgba(121, 255, 255, 0.12);
				border-color: rgba(121, 255, 255, 0.3);
				color: #79FFFF;
			}
		}
	}
}
</style>