<template>
    <div class="settings-content">
        <h2>隐私协议</h2>

        <h3>1. 信息收集范围</h3>
        <ul>
            <li><strong>必要信息：</strong>注册时的手机号/邮箱、设备标识符（用于安全验证）。</li>
            <li><strong>创作数据：</strong>上传的素材、剪辑工程文件、AI生成记录（加密存储，仅用于服务优化）。</li>
            <li><strong>行为数据：</strong>匿名化的功能使用统计（如"AI字幕"点击率），用于产品改进。</li>
        </ul>

        <h3>2. 信息使用目的</h3>
        <ul>
            <li>提供核心功能（如云渲染、协作同步）。</li>
            <li>个性化推荐（如基于历史操作的模板推荐，可关闭）。</li>
            <li>合规审计（如内容安全检测）。</li>
        </ul>

        <h3>3. 信息共享与第三方</h3>
        <ul>
            <li>不向任何第三方出售用户个人信息。</li>
            <li>仅在以下情况共享：法律要求、支付网关（如支付宝/Stripe）、CDN服务商（经脱敏处理）。</li>
        </ul>

        <h3>4. 数据安全</h3>
        <ul>
            <li><strong>传输加密：</strong>全站HTTPS + TLS 1.3。</li>
            <li><strong>存储加密：</strong>敏感数据AES-256加密，定期渗透测试。</li>
            <li><strong>访问控制：</strong>员工权限最小化原则，操作留痕审计。</li>
        </ul>

        <h3>5. 用户权利</h3>
        <ul>
            <li>查询/更正/删除个人信息：通过「设置-隐私中心」自助操作。</li>
            <li>撤回同意：关闭非必要权限后，部分功能可能受限。</li>
        </ul>

        <h3>6. 未成年人保护</h3>
        <p>未满18周岁用户需在监护人指导下使用，平台不主动收集未成年人生物识别信息。</p>
    </div>
</template>
<style scoped lang="scss">
@use './settings-shared';
</style>
