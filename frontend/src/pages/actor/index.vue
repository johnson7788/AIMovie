<script setup lang="ts">
import { useI18n } from 'vue-i18n'
useI18n()
</script>
<template>
    <div class="actor-page">
        <div class="actor-page-header">
            <div class="actor-page-header-title">
                <h1>{{ $t('actor.library') }}</h1>
            </div>
        </div>
    </div>
</template>