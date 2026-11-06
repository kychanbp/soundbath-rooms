# Sound Bath Rooms

A walkable WebXR valley in Bali with seven huts. Each hut has a different type of sound bath. The app is in English and Simplified Chinese (add `?lang=zh` to the address).
It runs in a desktop browser and on a VR headset.

| Room | Sound bath | Instruments | Reverberation (RT60 at 500 Hz) |
|---|---|---|---|
| Himalayan bowls | Struck and rubbed bronze bowls | 7 bowls, tingsha | 1.5 s |
| Crystal bowls | Sustained quartz bowls | 7 bowls, tuning fork | 6.0 s |
| Gong bath | Mallet rolls on gongs | 3 gongs | 2.2 s |
| Rain and chimes | Chimes with rain on glass | 4 chimes, ocean drum, rainstick | 1.7 s |
| Rin bells | Temple bells with water | 5 rin, suikinkutsu jar, bamboo | 0.55 s |
| Strings | Drone | Monochord, tanpura | 1.1 s |
| Cave drum | Rhythm in stone | Frame drum, didgeridoo, drips | 4.6 s |

## Start the world

1. Run `./serve.sh`.
2. Open `http://localhost:8000` in Chrome. On a phone on the same Wi-Fi, open the phone address that `serve.sh` shows.
3. Use headphones. The world uses head-related filtering for each instrument.

## Controls

- Desktop: drag to look. Push the on-screen circle up to walk and left or right to turn, or use W A S D. Push N to sit. Push M to lie down. Push H to hide the controls. Push F for full screen. Push E to close your eyes. Click an instrument to play it.
- On-screen buttons: Rooms goes straight to a room. Walk changes speed. The slider sets the volume.
- Headset: left stick to walk. Right stick to turn. Right A button to sit. Right B button to close or open your eyes.

## The valley

The site is modelled on the Jatiluwih rice terraces in Bali. Land shape and the far view use Copernicus GLO-30 elevation. Ground cover and far colour use Sentinel-2 true colour imagery. The terrace lines follow real contours. Rice and grass near the walker are drawn as 3D blades that follow the walker. Mount Batukaru stands on the skyline in its true direction. Wikimedia Commons photographs were used as visual reference only, and no photograph is in the build.

`scripts/make_land.py` plans the ground, paths, terraces and plant places. `scripts/make_palms.py` builds the palms and bananas. `blender/make_impostors.py` and `scripts/cut_cards.py` make the plant cards. `blender/build_hall.py` builds the valley and the hut exteriors.

## My figure

A plain figure walks in front of the camera on desktop and phones. It stops when you sit or lie down, and it never shows in a headset. Settings has a switch for it.

## Teachers

Each room has its own teacher who plays the instruments. The hand arrives at the instrument when the sound starts. The people come from Microsoft Rocketbox under the MIT licence (see `web/assets/teacher/LICENSE.md`).

## Phones

Android goes full screen when you tap Enter. iPhone Safari has no full screen for web pages: tap Share, then Add to Home Screen, and open it from the new icon.

Phones get smaller images, one live room at a time and simpler sound positions. Run `scripts/make_mobile.py` after a new bake to update `web/assets/m`.

## How the world is made

1. `scripts/fetch_assets.py` downloads CC0 textures, skies and models from Poly Haven.
2. `scripts/gen_tex.py` makes instrument textures.
3. `scripts/render_audio.py` calculates all samples with physical models. No sample is a recording.
4. `scripts/gen_rir.py` calculates one impulse response for each room.
5. `scripts/bake_all.sh <size> <samples> <rooms>` builds the rooms in Blender, bakes light in Cycles, removes noise with OIDN and exports glTF.
6. `web/` has the three.js app. `web/score.js` writes each session while it plays, so no session repeats.

## Sound model

Each bowl and bell is a set of decaying modes. Mode ratios come from published measurements. The sound engine puts each instrument at its position in the room. When you walk in the gallery, you hear the near room through the door with less treble. When you go in, the treble comes back.
