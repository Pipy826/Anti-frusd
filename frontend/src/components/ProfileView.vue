<template>
  <section class="screen profile-screen is-active">
    <StatusBar />
    <header class="profile-top">
      <img src="/assets/profile-avatar.png" alt="">
      <div><h1>反诈小卫士</h1><p>练就火眼金睛，守护财产安全</p><p>当前等级：<b>Lv.2</b></p></div>
      <span class="profile-badge"></span>
    </header>
    <div class="menu-card">
      <button @click="$emit('go', 'game')"><span class="menu-icon icon-medal"></span>我的成就 <i>›</i></button>
      <button><span class="menu-icon icon-guide"></span>使用说明 <i>›</i></button>
      <button><span class="menu-icon icon-help"></span>常见问题 <i>›</i></button>
      <button><span class="menu-icon icon-share"></span>分享给朋友 <i>›</i></button>
      <button @click="$emit('go', 'admin')"><span class="menu-icon icon-info"></span>运营后台 <i>›</i></button>
      <button><span class="menu-icon icon-info"></span>关于我们 <i>›</i></button>
    </div>
    <button class="clear" @click="$emit('clear')">清除本地记录</button>
    <TabBar active="profile" @go="$emit('go', $event)" />
  </section>
</template>

<script setup>
import StatusBar from './StatusBar.vue'
import TabBar from './TabBar.vue'

defineEmits(['clear', 'go'])
</script>
