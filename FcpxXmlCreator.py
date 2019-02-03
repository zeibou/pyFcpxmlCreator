
import xml.etree.ElementTree as ET
import os
from pyHiLightExtractor import MultiFilesReader
from pyHiLightExtractor.MultiFilesReader import HiLightDescriptor
from pyHiLightExtractor.MultiFilesReader import VideoDescriptor
import datetime
from dataclasses import dataclass
from typing import List
import time

fps = 60
format_4_3 = True
verbose = False

@dataclass
class HilightMultiClick:
    hilight : HiLightDescriptor
    nb_clicks : int

@dataclass
class FcpxExtendedDescriptor:
    start_time : int
    start_time_fps : int
    duration : int
    duration_fps : int

@dataclass
class AssetDescriptor:
    id : str
    videoDesc : VideoDescriptor
    fcpx_ext : FcpxExtendedDescriptor

@dataclass
class ClipDescriptor:
    name : str
    ref : str
    start : float
    duration : float


def add_mpeg_asset(root, video_desc):
    res = root.find("resources")
    nb_res = len(res)
    new_asset = ET.Element("asset")
    asset_id = "r"+str(nb_res + 1)
    new_asset.set("id", asset_id)
    new_asset.set("name", get_asset_name(video_desc.name))
    new_asset.set("src", "file://" + video_desc.path)
    res.append(new_asset)
    return AssetDescriptor(asset_id, video_desc, None)


def add_dummy_clip(spine, asset_desc : AssetDescriptor):
    new_asset = ET.Element("asset-clip")
    new_asset.set("ref", asset_desc.id)
    new_asset.set("name", get_asset_name(asset_desc.videoDesc.name))
    spine.append(new_asset)


def enrich_assets(root, assets):
    resources = root.find("resources")
    for res in resources.findall("asset"):
        asset = assets[res.get("name")]
        start = res.get("start")
        duration = res.get("duration")
        ext = FcpxExtendedDescriptor(*map(int, start[:-1].split('/')),*map(int, duration[:-1].split('/')))
        asset.id = res.get("id")
        asset.fcpx_ext = ext


def build_title_element(title_asset_id, text, offset):
    title_elt = ET.Element("title")
    title_elt.set("duration", "5s")
    title_elt.set("offset", offset)
    title_elt.set("start", "21605200/6000s")
    #offset="21597900/6000s" ref="r2" duration="59900/6000s" start="21605200/6000s"
    title_elt.set("lane", "1")
    title_elt.set("name", "title")
    title_elt.set("ref", title_asset_id)
    param_pos_elt = ET.Element("param")
    param_pos_elt.set("key", "9999/10902/10736/1/100/101")
    param_pos_elt.set("name", "Position")
    param_pos_elt.set("value", "245.11 -487.675")
    param_ali_elt = ET.Element("param")
    param_ali_elt.set("key", "9999/10902/10736/2/354/1156453060/401")
    param_ali_elt.set("name", "Alignment")
    param_ali_elt.set("value", "1 (Center)")
    text_elt = ET.Element("text")
    text_style_elt = ET.Element("text-style")
    text_style_elt.set("ref", "ts1")
    text_style_elt.text = text
    text_style_def_elt = ET.Element("text-style-def")
    text_style_def_elt.set("id", "ts1")
    text_style2_elt = ET.Element("text-style")
    text_style2_elt.set("alignment", "center")
    text_style2_elt.set("font", "Chalkduster")
    text_style2_elt.set("fontColor", "0.933208 1 0.925737 1")
    text_style2_elt.set("fontFace", "Regular")
    text_style2_elt.set("fontSize", "119")
    text_style2_elt.set("strokeColor", "0.000231543 0.00478462 0.0900643 1")
    text_style2_elt.set("strokeWidth", "4")

    title_elt.append(param_pos_elt)
    title_elt.append(param_ali_elt)
    text_elt.append(text_style_elt)
    title_elt.append(text_elt)
    text_style_def_elt.append(text_style2_elt)
    title_elt.append(text_style_def_elt)

    return title_elt


def get_asset_name(filepath):
    filename = os.path.basename(filepath)
    return os.path.splitext(filename)[0]


def open_template(template_xml_file):
    if not os.path.exists(template_xml_file):
        raise ValueError("template file not found")
    return ET.parse(template_xml_file)


def add_all_mpeg_assets(root, folder, assets):
    if verbose: print("Loading videos...")
    for h in MultiFilesReader.get_all_videos(folder, endswith=".mp4"):
        if not h.name in assets:
            assets[get_asset_name(h.name)] = add_mpeg_asset(root, h)
    if verbose:
        for a in assets: print(a, assets[a])
    return assets


def add_all_clips(spine, folder, assets, title_text):
    clip_descriptions = []
    for h in detect_multi_clicks(MultiFilesReader.get_all_hilights(folder, endswith=".mp4"), nb_seconds_interval = 3):
        hilight, duration, end_offset = h.hilight, *get_offset_bounds(h.nb_clicks)
        for clip in compute_clips(assets, hilight, duration, end_offset):
            clip_descriptions.append(clip)

    for i, clip_desc in enumerate(merge_clips(clip_descriptions)):
        clip = create_clip(clip_desc)
        spine.append(clip)

        # add title
        if i == 0:
            start = f"{int(clip_desc.start) + 3}s"
            clip.append(build_title_element("r4", title_text, start))


def get_offset_bounds(hilight_click_number):
    return (10 * hilight_click_number, 1)


def merge_clips(clips : List[ClipDescriptor]):
    # todo
    return clips


def get_video_start(asset):
    fcpx_ext = asset.fcpx_ext
    return fcpx_ext.start_time / fcpx_ext.start_time_fps

def compute_clips(assets, hilight, duration_seconds, end_offset_seconds):
    start_seconds = hilight.local_time.total_seconds() - duration_seconds - end_offset_seconds
    asset = assets[get_asset_name(hilight.name)]
    if start_seconds >= 0:
        yield ClipDescriptor(hilight.name, asset.id, start_seconds + get_video_start(asset), duration_seconds)
    else:
        # if hilight is early on a video, we need to insert the end of the previous video
        # adding end of the first clip
        previous = assets[get_asset_name(hilight.name)].videoDesc.previous_name
        if previous:
            asset_previous = assets[get_asset_name(previous)]
            previous_video_duration = asset_previous.videoDesc.total_time
            duration_to_show = max(1, -start_seconds)
            yield ClipDescriptor(previous, asset_previous.id, get_video_start(asset_previous) + previous_video_duration + start_seconds, duration_to_show)

        # adding beginning of the second clip
        if duration_seconds + start_seconds > 0:
            duration_to_show = max(1, duration_seconds + start_seconds)
            yield ClipDescriptor(hilight.name, asset.id, get_video_start(asset), duration_to_show)


def create_clip(clip_desc):
    if verbose: print(f'Adding Clip: {clip_desc}')
    clip = ET.Element("asset-clip")
    clip.set("name", get_asset_name(clip_desc.name))
    clip.set("ref", clip_desc.ref)
    clip.set("start", f"{int(clip_desc.start * fps)*100}/{fps}00s")
    clip.set("start", f"{int(clip_desc.start * fps)*100}/{fps}00s")
    clip.set("duration", f"{int(clip_desc.duration * fps)*100}/{fps}00s")
    #<adjust-transform scale="1.33 1.33"/>
    if format_4_3:
        zoom = ET.Element("adjust-transform")
        zoom.set("scale", "1.33 1.33")
        clip.append(zoom)
    return clip


def detect_multi_clicks(hilights : List[HiLightDescriptor], nb_seconds_interval=2):
    # todo loop reverse to keep first click of multi clicks
    # output detected multi clicks + discarded extra clicks
    # return filtered hilights with number of clicks associated (HilightMultiClick)
    next_hilight = None
    click_number = 0
    for h in hilights:#.reverse():
        print(h)
        #if next_hilight
        yield HilightMultiClick(h, 1)


def get_folder(date):
    return f"/Users/nicolas.seibert/Documents/foot/{date}"

def xml_creation_step_assets(date, template_path):
    tree = open_template(template_path)
    project = tree.getroot().find("library").find("event").find("project")
    project.set('name', f'{date}')
    spine = project.find("sequence").find("spine")
    assets = dict()
    folder = get_folder(date)
    add_all_mpeg_assets(tree.getroot(), folder, assets)
    for a in assets.values():
        add_dummy_clip(spine, a)
    start = "0s"
    spine[0].append(build_title_element("r2", "dummy", start))
    tree.write(os.path.join(folder, "autogen.fcpxml"))
    return assets


def xml_creation_step_clips(date, assets, waitForFile = False):
    folder = get_folder(date)
    filename = os.path.join(folder, f"{date}.fcpxml")
    if waitForFile:
        if not os.path.exists(filename):
            print(f"waiting for {filename}")
            while not os.path.exists(filename):
                time.sleep(1)
            time.sleep(5)  # give time for file to be fully exported

    d = datetime.datetime.strptime(date, "%Y-%m-%d")
    title_text = d.strftime("%B %d, %Y")
    tree = open_template(filename)
    project = tree.getroot().find("library").find("event").find("project")

    # identify_assets
    enrich_assets(tree.getroot(), assets)

    #remove dummy clips
    sequence = project.find("sequence")
    spine = sequence.find("spine")
    sequence.remove(spine)
    spine = ET.Element("spine")
    sequence.append(spine)

    # add all hilight clips
    add_all_clips(spine, folder, assets, title_text)

    # update sequence duration

    tree.write(f"/Users/nicolas.seibert/Documents/foot/{date}/{date}-final.fcpxml")


if __name__ == '__main__':
    verbose = True
    date = "2019-01-28"
    template_path = "/Users/nicolas.seibert/Documents/Projects/pyFcpxmlCreator/template.fcpxml"

    assets = xml_creation_step_assets(date, template_path)
    xml_creation_step_clips(date, assets, waitForFile = True)
