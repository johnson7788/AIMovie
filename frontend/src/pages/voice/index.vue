<script setup lang="ts">
import { useI18n } from 'vue-i18n'
useI18n()
</script>
<template>
    <div class="voice-page">
        <div class="voice-page-header">
            <div class="voice-page-header-title">
                <h1>{{ $t('voice.library') }}</h1>
            </div>
        </div>
    </div>
</template>