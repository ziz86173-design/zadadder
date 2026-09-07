import asyncio
import os
from datetime import datetime, timedelta
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantRequest, JoinChannelRequest
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, UserAlreadyParticipantError
from telethon.tl.types import KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonRow
import socket

# ============== إعدادات البوت ==============
BOT_TOKEN = "8656219234:AAExfUaal2mb1kG-MyH7TGjFxlcvmV4E4zk"  # ⚠️ ضع توكن البوت هنا

API_ID = 30051047
API_HASH = "21650e8511d73240d354f8d909d1fea1"

ALLOWED_USER_ID = 5107839417  # المستخدم المصرح له

USER_SESSION_FILE = "user_session.txt"

class TelegramControllerBot:
    def __init__(self):
        self.bot_client = None
        self.user_client = None
        self.target_entity = None
        self.source_entity = None
        self.active_users = []
        self.is_processing = False
        self.is_banned = False
        self.ban_end_time = None
        self.user_account_ready = False
        self.waiting_for_target = False
        self.waiting_for_source = False
        self.waiting_for_phone = False
        self.waiting_for_code = False
        self.phone_number = None
        
    def get_local_ip(self):
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "غير معروف"
    
    def save_user_session(self, session_string):
        try:
            with open(USER_SESSION_FILE, 'w') as f:
                f.write(session_string)
            print("[✓] تم حفظ جلسة المستخدم")
        except Exception as e:
            print(f"[!] خطأ في حفظ الجلسة: {e}")
    
    def load_user_session(self):
        try:
            if os.path.exists(USER_SESSION_FILE):
                with open(USER_SESSION_FILE, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"[!] خطأ في تحميل الجلسة: {e}")
        return None
    
    async def start_user_client_with_phone(self, phone):
        try:
            self.user_client = TelegramClient(StringSession(), API_ID, API_HASH)
            await self.user_client.connect()
            
            sent_code = await self.user_client.send_code_request(phone)
            self.phone_number = phone
            return True, "تم إرسال رمز التحقق. الرجاء إدخاله:"
            
        except Exception as e:
            return False, f"خطأ: {e}"
    
    async def complete_user_login(self, code):
        try:
            await self.user_client.sign_in(self.phone_number, code)
            session_string = self.user_client.session.save()
            self.save_user_session(session_string)
            
            me = await self.user_client.get_me()
            self.user_account_ready = True
            
            return True, me
        except Exception as e:
            if "Two-steps verification" in str(e):
                return "2fa", "مطلوب كلمة مرور التحقق بخطوتين"
            else:
                return False, f"خطأ: {e}"
    
    async def complete_2fa_login(self, password):
        try:
            await self.user_client.sign_in(password=password)
            session_string = self.user_client.session.save()
            self.save_user_session(session_string)
            
            me = await self.user_client.get_me()
            self.user_account_ready = True
            
            return True, me
        except Exception as e:
            return False, f"خطأ: {e}"
    
    async def start_user_client(self):
        try:
            session_string = self.load_user_session()
            
            if session_string:
                print("[+] جاري استعادة جلسة المستخدم...")
                self.user_client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
                await self.user_client.connect()
                
                if await self.user_client.is_user_authorized():
                    me = await self.user_client.get_me()
                    print(f"[✓] تم استعادة الحساب: {me.first_name} (@{me.username})")
                    self.user_account_ready = True
                    return True
            
            return False
            
        except Exception as e:
            print(f"[✗] خطأ في استعادة الجلسة: {e}")
            return False
    
    async def start_bot(self):
        try:
            self.bot_client = TelegramClient(StringSession(), API_ID, API_HASH)
            await self.bot_client.start(bot_token=BOT_TOKEN)
            
            me = await self.bot_client.get_me()
            print(f"[✓] تم تشغيل البوت: @{me.username}")
            return True
        except Exception as e:
            print(f"[✗] خطأ في تشغيل البوت: {e}")
            return False
    
    def create_menu_buttons(self):
        """إنشاء أزرار القائمة الرئيسية - الطريقة الصحيحة"""
        # إنشاء أزرار في صفوف
        row1 = KeyboardButtonRow([
            KeyboardButton("➕ إضافة حساب")
        ])
        row2 = KeyboardButtonRow([
            KeyboardButton("📱 استخدام حساب حالي")
        ])
        row3 = KeyboardButtonRow([
            KeyboardButton("📊 الحالة")
        ])
        
        # إنشاء الـ ReplyMarkup
        return ReplyKeyboardMarkup(
            rows=[row1, row2, row3],
            resize=True
        )
    
    async def handle_commands(self):
        """معالجة الأوامر"""
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_cmd(event):
            if event.sender_id != ALLOWED_USER_ID:
                await event.reply("⛔ **غير مصرح لك باستخدام هذا البوت!**")
                return
            
            buttons = self.create_menu_buttons()
            
            msg = f"""
👋 **مرحباً بك في بوت التحكم!**

🖥️ **الآيبي:** {self.get_local_ip()}
👤 **معرفك:** {event.sender_id}

📌 **اختر أحد الخيارات أدناه:**
"""
            
            await event.reply(msg, buttons=buttons)
        
        @self.bot_client.on(events.NewMessage(pattern='➕ إضافة حساب'))
        async def add_account_button(event):
            if event.sender_id != ALLOWED_USER_ID:
                return
            
            await event.reply("📱 **يرجى إدخال رقم الهاتف بصيغة دولية:**\nمثال: +201234567890")
            self.waiting_for_phone = True
        
        @self.bot_client.on(events.NewMessage(pattern='📱 استخدام حساب حالي'))
        async def use_account_button(event):
            if event.sender_id != ALLOWED_USER_ID:
                return
            
            if self.user_account_ready:
                try:
                    me = await self.user_client.get_me()
                    await event.reply(f"""
✅ **الحساب الحالي نشط:**

👤 **الاسم:** {me.first_name}
🆔 **المعرف:** @{me.username if me.username else 'لا يوجد'}
🆔 **الآيدي:** `{me.id}`

🔹 **/set_target** - تعيين المجموعة المستهدفة
🔹 **/set_source** - تعيين مجموعة المصدر
🔹 **/start_adding** - بدء الإضافة
""")
                except:
                    self.user_account_ready = False
                    await event.reply("❌ **انتهت صلاحية الجلسة!** استخدم /add_account لإضافة حساب جديد.")
            else:
                await event.reply("❌ **لا يوجد حساب نشط!** استخدم /add_account لإضافة حساب.")
        
        @self.bot_client.on(events.NewMessage(pattern='📊 الحالة'))
        async def status_button(event):
            if event.sender_id != ALLOWED_USER_ID:
                return
            
            status = f"""
📊 **حالة البوت**

🖥️ **الآيبي:** {self.get_local_ip()}
👤 **الحساب:** {'✅ متصل' if self.user_account_ready else '❌ غير متصل'}
📌 **المجموعة المستهدفة:** {self.target_entity.title if self.target_entity else '❌ غير محددة'}
📌 **مجموعة المصدر:** {self.source_entity.title if self.source_entity else '❌ غير محددة'}
👥 **الأعضاء المجموعين:** {len(self.active_users)}
🔄 **حالة المعالجة:** {'جاري' if self.is_processing else 'متوقف'}
⛔ **حظر مؤقت:** {'✅ نعم' if self.is_banned else '❌ لا'}
"""
            if self.is_banned and self.ban_end_time:
                status += f"⏳ **ينتهي الحظر في:** {self.ban_end_time.strftime('%H:%M:%S')}"
            
            await event.reply(status)
        
        @self.bot_client.on(events.NewMessage(pattern='/add_account'))
        async def add_account_cmd(event):
            if event.sender_id != ALLOWED_USER_ID:
                await event.reply("⛔ غير مصرح لك!")
                return
            
            await event.reply("📱 **يرجى إدخال رقم الهاتف بصيغة دولية:**\nمثال: +201234567890")
            self.waiting_for_phone = True
        
        @self.bot_client.on(events.NewMessage(pattern='/use_account'))
        async def use_account_cmd(event):
            if event.sender_id != ALLOWED_USER_ID:
                await event.reply("⛔ غير مصرح لك!")
                return
            
            if self.user_account_ready:
                try:
                    me = await self.user_client.get_me()
                    await event.reply(f"""
✅ **الحساب الحالي نشط:**

👤 **الاسم:** {me.first_name}
🆔 **المعرف:** @{me.username if me.username else 'لا يوجد'}
🆔 **الآيدي:** `{me.id}`

🔹 **/set_target** - تعيين المجموعة المستهدفة
🔹 **/set_source** - تعيين مجموعة المصدر
🔹 **/start_adding** - بدء الإضافة
""")
                except:
                    self.user_account_ready = False
                    await event.reply("❌ **انتهت صلاحية الجلسة!** استخدم /add_account لإضافة حساب جديد.")
            else:
                await event.reply("❌ **لا يوجد حساب نشط!** استخدم /add_account لإضافة حساب.")
        
        @self.bot_client.on(events.NewMessage)
        async def handle_messages(event):
            if event.sender_id != ALLOWED_USER_ID:
                return
            
            # معالجة إدخال رقم الهاتف
            if self.waiting_for_phone:
                phone = event.text.strip()
                if phone.startswith('+') and phone[1:].isdigit():
                    self.waiting_for_phone = False
                    await event.reply(f"📱 **جاري تسجيل الدخول بالرقم:** `{phone}`")
                    
                    success, msg = await self.start_user_client_with_phone(phone)
                    if success:
                        self.waiting_for_code = True
                        await event.reply(f"🔑 **{msg}**")
                    else:
                        await event.reply(f"❌ **{msg}**")
                else:
                    await event.reply("❌ **رقم غير صحيح!** يجب أن يبدأ بـ + متبوعاً بالأرقام.\nمثال: +201234567890")
                return
            
            # معالجة إدخال رمز التحقق
            if self.waiting_for_code:
                code = event.text.strip()
                if code.isdigit():
                    self.waiting_for_code = False
                    await event.reply("🔐 **جاري التحقق من الرمز...**")
                    
                    result = await self.complete_user_login(code)
                    if result[0] == "2fa":
                        self.waiting_for_code = True
                        await event.reply(f"🔑 **{result[1]}**")
                    elif result[0]:
                        me = result[1]
                        await event.reply(f"""
✅ **تم تسجيل الدخول بنجاح!**

👤 **الاسم:** {me.first_name}
🆔 **المعرف:** @{me.username if me.username else 'لا يوجد'}
🆔 **الآيدي:** `{me.id}`

📌 **استخدم /start للعودة إلى القائمة الرئيسية**
""")
                    else:
                        await event.reply(f"❌ **{result[1]}**")
                        self.waiting_for_code = True
                else:
                    # قد تكون كلمة مرور التحقق بخطوتين
                    password = event.text.strip()
                    self.waiting_for_code = False
                    
                    result = await self.complete_2fa_login(password)
                    if result[0]:
                        me = result[1]
                        await event.reply(f"""
✅ **تم تسجيل الدخول بنجاح!**

👤 **الاسم:** {me.first_name}
🆔 **المعرف:** @{me.username if me.username else 'لا يوجد'}
🆔 **الآيدي:** `{me.id}`

📌 **استخدم /start للعودة إلى القائمة الرئيسية**
""")
                    else:
                        await event.reply(f"❌ **{result[1]}**")
                        self.waiting_for_code = True
                return
        
        @self.bot_client.on(events.NewMessage(pattern='/set_target'))
        async def set_target_cmd(event):
            if event.sender_id != ALLOWED_USER_ID:
                await event.reply("⛔ غير مصرح لك!")
                return
            
            if not self.user_account_ready:
                await event.reply("❌ **الرجاء إضافة حساب أولاً!** استخدم /add_account")
                return
            
            await event.reply("🔗 **أرسل رابط المجموعة المستهدفة:**\nمثال: https://t.me/group_name")
            self.waiting_for_target = True
        
        @self.bot_client.on(events.NewMessage)
        async def handle_target_setup(event):
            if event.sender_id != ALLOWED_USER_ID:
                return
            
            if self.waiting_for_target and not event.text.startswith('/'):
                link = event.text.strip()
                self.waiting_for_target = False
                await event.reply(f"[+] **جاري التحقق من:** {link}")
                
                entity = await self.extract_group(link)
                if entity:
                    self.target_entity = entity
                    await event.reply(f"""
✅ **تم تعيين المجموعة المستهدفة!**

📌 **الاسم:** {entity.title}
👥 **الأعضاء:** {getattr(entity, 'participants_count', 'غير معروف')}

📌 **استخدم /set_source لتعيين مجموعة المصدر**
""")
                else:
                    await event.reply("❌ **رابط غير صالح!** تأكد من الرابط وحاول مرة أخرى.")
                    self.waiting_for_target = True
        
        @self.bot_client.on(events.NewMessage(pattern='/set_source'))
        async def set_source_cmd(event):
            if event.sender_id != ALLOWED_USER_ID:
                await event.reply("⛔ غير مصرح لك!")
                return
            
            if not self.user_account_ready:
                await event.reply("❌ **الرجاء إضافة حساب أولاً!** استخدم /add_account")
                return
            
            await event.reply("🔗 **أرسل رابط مجموعة المصدر:**\nمثال: https://t.me/source_group")
            self.waiting_for_source = True
        
        @self.bot_client.on(events.NewMessage)
        async def handle_source_setup(event):
            if event.sender_id != ALLOWED_USER_ID:
                return
            
            if self.waiting_for_source and not event.text.startswith('/'):
                link = event.text.strip()
                self.waiting_for_source = False
                await event.reply(f"[+] **جاري التحقق من:** {link}")
                
                entity = await self.extract_group(link)
                if entity:
                    self.source_entity = entity
                    await event.reply(f"""
✅ **تم تعيين مجموعة المصدر!**

📌 **الاسم:** {entity.title}
👥 **الأعضاء:** {getattr(entity, 'participants_count', 'غير معروف')}

📌 **استخدم /start_adding لبدء إضافة الأعضاء**
""")
                else:
                    await event.reply("❌ **رابط غير صالح!** تأكد من الرابط وحاول مرة أخرى.")
                    self.waiting_for_source = True
        
        @self.bot_client.on(events.NewMessage(pattern='/start_adding'))
        async def start_adding_cmd(event):
            if event.sender_id != ALLOWED_USER_ID:
                await event.reply("⛔ غير مصرح لك!")
                return
            
            if not self.user_account_ready:
                await event.reply("❌ **الرجاء إضافة حساب أولاً!** استخدم /add_account")
                return
            
            if not self.target_entity or not self.source_entity:
                await event.reply("❌ **الرجاء تعيين المجموعتين أولاً!**\nاستخدم /set_target و /set_source")
                return
            
            if self.is_processing:
                await event.reply("⚠️ **عملية جارية بالفعل!** استخدم /stop للإيقاف")
                return
            
            await event.reply(f"""
[+] **بدء عملية الإضافة...**

🔹 **مجموعة المصدر:** {self.source_entity.title}
🔹 **المجموعة المستهدفة:** {self.target_entity.title}
🔹 **الوضع:** سريع (10 عمليات متوازية)

⏳ **جاري جمع الأعضاء...**
""")
            
            self.is_processing = True
            
            users = await self.collect_users()
            
            if not users:
                await event.reply("❌ **لم يتم العثور على أعضاء في مجموعة المصدر!**")
                self.is_processing = False
                return
            
            await event.reply(f"""
✅ **تم العثور على {len(users)} عضو!**

⏳ **جاري الإضافة...**
""")
            
            added, failed = await self.add_members_fast()
            self.is_processing = False
            
            success_rate = (added/(added+failed)*100) if (added+failed) > 0 else 0
            
            await event.reply(f"""
✅ **اكتملت العملية!**

✅ **تمت الإضافة بنجاح:** {added}
❌ **فشل الإضافة:** {failed}
📊 **نسبة النجاح:** {success_rate:.1f}%

📌 **استخدم /start للعودة إلى القائمة الرئيسية**
""")
        
        @self.bot_client.on(events.NewMessage(pattern='/status'))
        async def status_cmd(event):
            if event.sender_id != ALLOWED_USER_ID:
                await event.reply("⛔ غير مصرح لك!")
                return
            
            status = f"""
📊 **حالة البوت**

🖥️ **الآيبي:** {self.get_local_ip()}
👤 **الحساب:** {'✅ متصل' if self.user_account_ready else '❌ غير متصل'}
📌 **المجموعة المستهدفة:** {self.target_entity.title if self.target_entity else '❌ غير محددة'}
📌 **مجموعة المصدر:** {self.source_entity.title if self.source_entity else '❌ غير محددة'}
👥 **الأعضاء المجموعين:** {len(self.active_users)}
🔄 **حالة المعالجة:** {'جاري' if self.is_processing else 'متوقف'}
⛔ **حظر مؤقت:** {'✅ نعم' if self.is_banned else '❌ لا'}
"""
            if self.is_banned and self.ban_end_time:
                status += f"⏳ **ينتهي الحظر في:** {self.ban_end_time.strftime('%H:%M:%S')}"
            
            await event.reply(status)
        
        @self.bot_client.on(events.NewMessage(pattern='/stop'))
        async def stop_cmd(event):
            if event.sender_id != ALLOWED_USER_ID:
                await event.reply("⛔ غير مصرح لك!")
                return
            
            self.is_processing = False
            await event.reply("🛑 **تم إيقاف العملية!**")
        
        @self.bot_client.on(events.NewMessage(pattern='/help'))
        async def help_cmd(event):
            if event.sender_id != ALLOWED_USER_ID:
                await event.reply("⛔ غير مصرح لك!")
                return
            
            await event.reply("""
📖 **قائمة الأوامر:**

🔹 **/start** - القائمة الرئيسية
🔹 **/add_account** - إضافة حساب جديد
🔹 **/use_account** - استخدام الحساب الحالي
🔹 **/set_target** - تعيين المجموعة المستهدفة
🔹 **/set_source** - تعيين مجموعة المصدر
🔹 **/start_adding** - بدء إضافة الأعضاء
🔹 **/status** - عرض الحالة
🔹 **/stop** - إيقاف العملية
🔹 **/help** - عرض هذه الرسالة

━━━━━━━━━━━━━━━━━━━━━

📌 **طريقة الاستخدام:**
1. أضف حساب باستخدام /add_account
2. عين المجموعة المستهدفة /set_target
3. عين مجموعة المصدر /set_source
4. ابدأ الإضافة /start_adding
""")
    
    async def extract_group(self, link):
        try:
            link = link.strip()
            if 't.me/' in link:
                username = link.split('t.me/')[-1].split('/')[0]
            else:
                username = link.replace('@', '')
            
            entity = await self.user_client.get_entity(f'@{username}')
            
            try:
                await self.user_client(GetParticipantRequest(
                    channel=entity,
                    participant=await self.user_client.get_me()
                ))
            except:
                await self.user_client(JoinChannelRequest(entity))
                await asyncio.sleep(2)
            
            return entity
        except Exception as e:
            print(f"[!] خطأ في الاستخراج: {e}")
            return None
    
    async def collect_users(self):
        self.active_users = []
        
        try:
            await self.bot_client.send_message(ALLOWED_USER_ID, "[+] جاري جمع المستخدمين...")
            
            messages = await self.user_client.get_messages(self.source_entity, limit=5000)
            user_ids = set()
            
            for msg in messages:
                if msg.sender_id and msg.sender_id > 0:
                    user_ids.add(msg.sender_id)
            
            self.active_users = list(user_ids)
            print(f"[+] تم العثور على {len(self.active_users)} مستخدم")
            return self.active_users
        except Exception as e:
            print(f"[!] خطأ في الجمع: {e}")
            return []
    
    async def add_members_fast(self):
        added = 0
        failed = 0
        semaphore = asyncio.Semaphore(10)
        
        tasks = [asyncio.create_task(self.add_single(user_id, semaphore)) 
                 for user_id in self.active_users]
        
        completed = 0
        total = len(tasks)
        
        for coro in asyncio.as_completed(tasks):
            success, _, error = await coro
            completed += 1
            
            if success:
                added += 1
            else:
                failed += 1
            
            if completed % 20 == 0 or completed == total:
                progress_msg = f"📊 **التقدم:** {completed}/{total}\n✅ **نجاح:** {added}\n❌ **فشل:** {failed}"
                try:
                    await self.bot_client.send_message(ALLOWED_USER_ID, progress_msg)
                except:
                    pass
        
        return added, failed
    
    async def add_single(self, user_id, semaphore):
        async with semaphore:
            try:
                user = await self.user_client.get_entity(user_id)
                await self.user_client(InviteToChannelRequest(
                    channel=self.target_entity,
                    users=[user]
                ))
                return True, user_id, None
                
            except FloodWaitError as e:
                wait = e.seconds
                self.is_banned = True
                self.ban_end_time = datetime.now() + timedelta(seconds=wait)
                print(f"[!] تم الحظر لمدة {wait} ثانية، يستأنف في {self.ban_end_time.strftime('%H:%M:%S')}")
                
                try:
                    await self.bot_client.send_message(ALLOWED_USER_ID, f"""
⚠️ **تم حظر الحساب مؤقتاً!**

⏳ **المدة:** {wait} ثانية ({wait/60:.1f} دقيقة)
⏰ **يستأنف في:** {self.ban_end_time.strftime('%H:%M:%S')}

📌 **سيستأنف العمل تلقائياً بعد انتهاء الحظر**
""")
                except:
                    pass
                
                await asyncio.sleep(wait)
                self.is_banned = False
                return False, user_id, "flood"
                
            except UserPrivacyRestrictedError:
                return False, user_id, "خصوصية"
                
            except UserAlreadyParticipantError:
                return True, user_id, "موجود"
                
            except Exception as e:
                return False, user_id, str(e)
    
    async def run(self):
        print("="*60)
        print("🤖 بوت التحكم في تيليجرام")
        print("="*60)
        
        if not await self.start_bot():
            print("[✗] فشل تشغيل البوت")
            return
        
        await self.handle_commands()
        
        print(f"""
[✓] ========== النظام جاهز ==========
[✓] البوت: متصل
[✓] الآيبي: {self.get_local_ip()}
[✓] المستخدم المصرح له: {ALLOWED_USER_ID}

[+] البوت يعمل. أرسل /start للبدء.
""")
        
        await self.bot_client.run_until_disconnected()

if __name__ == "__main__":
    try:
        bot = TelegramControllerBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n[!] تم الإيقاف يدوياً")
    except Exception as e:
        print(f"[✗] خطأ: {e}")