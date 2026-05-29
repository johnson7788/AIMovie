<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useRoute } from 'vue-router';
const route = useRoute();
const article = route.params.article as string | number
const details = ref<any>();
const getArticle = () => {
    $http.get('/app/article/api/Article/details', { params: { id:article } }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            details.value = res.data;
        }
    })
}
onMounted(() => {
    getArticle();
})
</script>
<template>
    <div v-html="details?.content.content"></div>
</template>