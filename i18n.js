// All on-screen text. Add a language by adding a block here.
export const STR = {
  en: {
    appTitle: 'Sound Bath Rooms', intro: 'A jungle valley in Bali with seven huts. Each hut holds a different sound bath. Follow the paths, find a hut, and stay as long as you like.',
    enter: 'Enter', headphones: 'Best with headphones', opening: 'Opening the doors…', openingPhone: 'Opening the doors. This can take a minute on a phone…',
    rooms: 'Huts', sit: 'Sit', lie: 'Lie down', up: 'Get up', eyes: 'Close eyes', eyesOpen: 'Tap to open your eyes', sound: 'Sound', muted: 'Muted', full: 'Full screen', exit: 'Exit', settings: 'Settings',
    goto: 'Go to a hut', here: 'You are here', volume: 'Volume', speed: 'Walking speed', slow: 'Slow', fast: 'Fast', seeMe: 'Show my figure', hide: 'Hide controls', end: 'End session', language: 'Language',
    helpTouch: 'Drag to look. Push the circle to walk and turn. Tap an instrument to play it.', helpMouse: 'Drag to look. Push the circle, or use W A S D, to walk. Click an instrument to play it. H hides the controls.',
    ended: 'The session has ended', ended2: 'Stay as long as you like', tapSound: 'Tap the screen for sound', tapSound2: 'Your phone paused the sound', walkFirst: 'Walk into a hut first',
    iosTitle: 'Full screen on iPhone', iosBody: 'Safari on iPhone does not let web pages go full screen. Add this page to your Home Screen, and it opens full screen from there.', ios1: 'Tap the Share button in Safari', ios2: 'Tap Add to Home Screen', ios3: 'Open Sound Bath from the new icon', close: 'Got it',
    path: 'Forest path',
    t: { himalayan: 'Himalayan bowls', crystal: 'Crystal bowls', gong: 'Gong bath', rain: 'Rain and chimes', rin: 'Rin bells', strings: 'Strings', cave: 'Cave drum' },
    s: { himalayan: 'Seven hammered bronze bowls', crystal: 'Frosted quartz bowls under a skylight', gong: 'Three gongs in a dark room', rain: 'Chimes, ocean drum and rain on glass', rin: 'Temple bells and a water jar', strings: 'Monochord and tanpura', cave: 'Frame drum and didgeridoo in stone' },
  },
  zh: {
    appTitle: '声浴小屋', intro: '巴厘岛的丛林山谷里有七座小屋，每座小屋都有一种不同的声浴。沿着小径走，找到一座小屋，想待多久就待多久。',
    enter: '进入', headphones: '建议使用耳机', opening: '正在开门…', openingPhone: '正在开门，手机上可能需要一分钟…',
    rooms: '小屋', sit: '坐下', lie: '躺下', up: '起身', eyes: '闭上眼睛', eyesOpen: '轻点屏幕睁开眼睛', sound: '声音', muted: '静音', full: '全屏', exit: '退出', settings: '设置',
    goto: '前往小屋', here: '您在这里', volume: '音量', speed: '步行速度', slow: '慢', fast: '快', seeMe: '显示我的身影', hide: '隐藏控件', end: '结束体验', language: '语言',
    helpTouch: '拖动屏幕可环顾四周，推动圆盘可行走和转向，轻点乐器可演奏。', helpMouse: '拖动画面可环顾四周，推动圆盘或按 W A S D 可行走，点击乐器可演奏，按 H 可隐藏控件。',
    ended: '本次声浴已结束', ended2: '想待多久就待多久', tapSound: '请轻点屏幕以播放声音', tapSound2: '手机暂停了声音', walkFirst: '请先走进一座小屋',
    iosTitle: 'iPhone 全屏', iosBody: 'iPhone 上的 Safari 不允许网页全屏。把此页面添加到主屏幕后，从主屏幕打开即可全屏。', ios1: '点按 Safari 的“分享”按钮', ios2: '点按“添加到主屏幕”', ios3: '从新图标打开“声浴小屋”', close: '知道了',
    path: '丛林小径',
    t: { himalayan: '喜马拉雅颂钵', crystal: '水晶钵', gong: '锣浴', rain: '雨声与风铃', rin: '寺院铃音', strings: '弦乐', cave: '洞穴鼓' },
    s: { himalayan: '七只手工锤制的青铜钵', crystal: '天窗下的磨砂水晶钵', gong: '暗室中的三面大锣', rain: '风铃、海浪鼓与玻璃上的雨声', rin: '寺院铃与水琴窟', strings: '单弦琴与坦布拉琴', cave: '石洞中的手鼓与迪吉里杜管' },
  },
};
export function pickLang(q) {
  let v = q; try { v = v || localStorage.getItem('lang'); } catch { }
  if (!v) v = /^zh/i.test(navigator.language || '') ? 'zh' : 'en';
  return STR[v] ? v : 'en';
}
