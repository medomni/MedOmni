"""Probabilities of 39 fundus conditions from RETFound fine-tuned on JSIEC."""
import os
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from contract import Degraded, labels, text

FAMILY = 'fundus-photography-2d'
# Head index order = the 39 JSIEC training folders sorted by name ("0.0.Normal" ... "9.Pathological myopia";
# RETFound BENCHMARK.md JSIEC split); labels are those folder names without the index, abbreviations expanded.
CLASSES = ('normal', 'tessellated_fundus', 'large_optic_cup', 'diabetic_retinopathy_stage_1', 'diabetic_retinopathy_stage_2', 'diabetic_retinopathy_stage_3', 'possible_glaucoma', 'optic_atrophy', 'severe_hypertensive_retinopathy', 'disc_swelling_and_elevation', 'dragged_disc', 'congenital_disc_abnormality', 'retinitis_pigmentosa', 'bietti_crystalline_dystrophy', 'peripheral_retinal_degeneration_and_break', 'myelinated_nerve_fiber', 'vitreous_particles', 'fundus_neoplasm', 'branch_retinal_vein_occlusion', 'central_retinal_vein_occlusion', 'massive_hard_exudates', 'yellow_white_spots_flecks', 'cotton_wool_spots', 'vessel_tortuosity', 'chorioretinal_atrophy_coloboma', 'preretinal_hemorrhage', 'fibrosis', 'laser_spots', 'silicone_oil_in_eye', 'blurred_fundus_without_proliferative_dr', 'blurred_fundus_with_suspected_proliferative_dr', 'retinal_artery_occlusion', 'rhegmatogenous_retinal_detachment', 'central_serous_chorioretinopathy', 'vogt_koyanagi_harada_disease', 'maculopathy', 'epiretinal_membrane', 'macular_hole', 'pathological_myopia',)


def load():
    from models_vit import RETFound_mae
    path = Path(os.environ.get('RETFOUND_HEAD_WEIGHTS', '/opt/weights/model.pth'))
    state = torch.load(path, map_location='cpu', weights_only=True, mmap=True)
    model = RETFound_mae(global_pool=True, num_classes=len(CLASSES))
    model.load_state_dict(state, strict=True)
    return model.eval()


def encode(sample, options):
    pixels = sample['pixels']
    if pixels.ndim != 3 or pixels.shape[2] != 3 or pixels.dtype != np.uint8:
        raise Degraded('RETFound requires an eight-bit colour fundus image')
    transform = transforms.Compose([
        transforms.Resize(256, interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize((.485, .456, .406), (.229, .224, .225)),
    ])
    with torch.inference_mode():
        # RETFound's forward_features predates timm's attn_mask argument; pool, then head.
        model = options['_model']
        logits = model.head(model.forward_features(transform(Image.fromarray(pixels)).unsqueeze(0))).reshape(-1)
    probs = torch.softmax(logits, dim=0)
    if probs.shape != (len(CLASSES),) or not torch.isfinite(probs).all():
        raise RuntimeError('RETFound produced invalid probabilities')
    values = [float(p) for p in probs]
    items = [dict(label=name, value=value) for name, value in zip(CLASSES, values)]
    top = sorted(zip(CLASSES, values), key=lambda pair: -pair[1])[:3]
    summary = 'Top findings: ' + '; '.join(f"{name.replace('_', ' ')} {value:.2f}" for name, value in top)
    return [labels(items, 'probability'), text(summary)]
