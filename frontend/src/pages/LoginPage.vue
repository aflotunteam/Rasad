<script setup lang="ts">
import { ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck, UserRound } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BrandMark from '@/components/layout/BrandMark.vue'
import SyntheticBadge from '@/components/ui/SyntheticBadge.vue'
import { ApiError } from '@/services/http'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const show = ref(false)
const loading = ref(false)
const error = ref<string | null>(route.query.expired ? 'Sessiya muddati tugagan. Qaytadan kiring.' : null)

const demo = [
  { username: 'tahlilchi', password: 'Tahlil123!', role: 'Tahlilchi', note: 'Namangan viloyati' },
  { username: 'admin', password: 'Admin123!', role: 'Administrator', note: 'Barcha bo‘limlar' },
  { username: 'rahbar', password: 'Rahbar123!', role: 'Rahbar', note: 'Boshqaruv ko‘rsatkichlari' },
  { username: 'auditor', password: 'Audit123!', role: 'Auditor', note: 'Audit va nazorat' },
]

const chain = ['Ma’lumot sifati', 'Subyektni moslashtirish', 'Tahliliy belgilar', 'Modellar', 'Kalibrlash', 'Xavf bahosi', 'Ishonch darajasi', 'Sabablar', 'Ekspert qarori']

function fill(d: (typeof demo)[number]) {
  username.value = d.username
  password.value = d.password
  error.value = null
}

async function submit() {
  if (!username.value || !password.value) {
    error.value = 'Login va parolni kiriting'
    return
  }
  loading.value = true
  error.value = null
  try {
    await auth.login(username.value.trim(), password.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : '/'
    router.replace(next)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Kirishda xatolik yuz berdi'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <section class="intro" aria-label="RASAD haqida">
      <div class="brand">
        <BrandMark :size="44" />
        <div>
          <div class="brand-name">RASAD</div>
          <div class="brand-sub">Intellektual iqtisodiy xavf tahlili platformasi</div>
        </div>
      </div>

      <div class="intro-body">
        <h1>Qaysi holat qo‘shimcha ekspert tahlilini birinchi navbatda talab qiladi va nima sababdan?</h1>
        <p>
          RASAD ko‘p manbali iqtisodiy ma’lumotlarni tekshiradi, g‘ayrioddiy holatlarni aniqlaydi, xavf bahosini
          ishonch darajasi va sabablari bilan ko‘rsatadi. Yakuniy qaror vakolatli ekspertda qoladi.
        </p>
        <ol class="chain" aria-label="Tahlil zanjiri">
          <li v-for="(c, i) in chain" :key="c"><span class="num">{{ String(i + 1).padStart(2, '0') }}</span>{{ c }}</li>
        </ol>
      </div>

      <div class="intro-foot">
        <ShieldCheck :size="16" />
        RASAD aybni aniqlamaydi va yakuniy huquqiy qaror chiqarmaydi.
      </div>
    </section>

    <section class="form-side">
      <form class="form card" novalidate @submit.prevent="submit">
        <div class="form-head">
          <h2>Tizimga kirish</h2>
          <SyntheticBadge compact />
        </div>
        <p class="muted small">Namoyish muhiti. Barcha ma’lumotlar sun’iy yaratilgan.</p>

        <label class="field">
          <span class="field-label">Login</span>
          <span class="input-icon">
            <UserRound :size="16" />
            <input v-model="username" class="input" autocomplete="username" autofocus />
          </span>
        </label>
        <label class="field">
          <span class="field-label">Parol</span>
          <span class="input-icon">
            <LockKeyhole :size="16" />
            <input v-model="password" class="input" :type="show ? 'text' : 'password'" autocomplete="current-password" />
            <button type="button" class="eye" :aria-label="show ? 'Parolni yashirish' : 'Parolni ko‘rsatish'" @click="show = !show">
              <component :is="show ? EyeOff : Eye" :size="16" />
            </button>
          </span>
        </label>

        <div v-if="error" class="notice notice-danger" role="alert">{{ error }}</div>

        <button class="btn btn-primary submit" type="submit" :disabled="loading">
          {{ loading ? 'Tekshirilmoqda…' : 'Kirish' }}
          <ArrowRight v-if="!loading" :size="16" />
        </button>

        <div class="demo">
          <div class="section-label">Namoyish hisoblari</div>
          <button v-for="d in demo" :key="d.username" type="button" class="demo-item" @click="fill(d)">
            <span class="demo-role">{{ d.role }}</span>
            <span class="muted xs">{{ d.note }}</span>
            <span class="spacer" />
            <code class="xs">{{ d.username }}</code>
          </button>
        </div>
      </form>
    </section>
  </div>
</template>

<style scoped>
.login {
  display: grid;
  grid-template-columns: minmax(520px, 1.1fr) 1fr;
  min-height: 100vh;
}

.intro {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 44px 56px;
  background:
    radial-gradient(900px 480px at 85% 10%, rgba(33, 109, 243, 0.22), transparent 60%),
    radial-gradient(700px 400px at 10% 100%, rgba(56, 189, 248, 0.12), transparent 60%),
    var(--navy);
  color: var(--on-dark);
  overflow: hidden;
}

.brand { display: flex; align-items: center; gap: 14px; }
.brand-name { font-size: 22px; font-weight: 760; letter-spacing: 0.16em; color: #fff; }
.brand-sub { font-size: var(--fs-sm); color: var(--on-dark-muted); }

.intro-body { margin: auto 0; max-width: 620px; }

.intro-body h1 {
  color: #fff;
  font-size: 30px;
  line-height: 1.25;
  font-weight: 680;
  letter-spacing: -0.02em;
}

.intro-body p { margin-top: 16px; color: #b8c7dc; font-size: 15px; line-height: 1.6; }

.chain {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
}

.chain li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 11px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.035);
  font-size: var(--fs-sm);
  color: #d5e0ee;
}

.chain li span { color: var(--cyan); font-size: 11px; font-weight: 650; }

.intro-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-sm);
  color: var(--on-dark-muted);
}

.form-side { display: grid; place-items: center; padding: 32px; }

.form {
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 30px 30px 24px;
  box-shadow: var(--shadow-md);
}

.form-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.form-head h2 { font-size: 22px; }

.input-icon { position: relative; display: block; }
.input-icon > svg { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--muted); }
.input-icon .input { height: 42px; padding-left: 38px; }

.eye {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}

.eye:hover { background: var(--surface-3); }
.submit { height: 42px; margin-top: 4px; font-size: var(--fs-base); }

.demo { margin-top: 8px; padding-top: 14px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 6px; }

.demo-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--surface-2);
  cursor: pointer;
  text-align: left;
  transition: border-color var(--t-fast), background var(--t-fast);
}

.demo-item:hover { border-color: var(--blue-100); background: var(--blue-50); }
.demo-role { font-size: var(--fs-md); font-weight: 600; color: var(--navy); }
.demo-item code { color: var(--muted); }

@media (max-width: 1100px) {
  .login { grid-template-columns: 1fr; }
  .intro { display: none; }
}
</style>
