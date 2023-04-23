import trimesh
import numpy as np
import json
import os.path as osp

def load_inseg(pth_ply):
    cloud_pd = trimesh.load(pth_ply, process=False)
    points_pd = cloud_pd.vertices
    segments_pd = cloud_pd.metadata['_ply_raw']['vertex']['data']['label'].flatten()

    return cloud_pd, points_pd, segments_pd

def get_scan_ids(dirname, split):
    filepath = osp.join(dirname, 'scannetv2_{}.txt'.format(split))
    scan_ids = np.genfromtxt(filepath, dtype = str)
    return scan_ids

def scannet_get_instance_ply(plydata, segs, aggre, random_color=False):
    ''' map idx to segments '''
    seg_map = dict()
    for idx in range(len(segs['segIndices'])):
        seg = segs['segIndices'][idx]
        if seg in seg_map:
            seg_map[seg].append(idx)
        else:
            seg_map[seg] = [idx]
   
    ''' Group segments '''
    aggre_seg_map = dict()
    for segGroup in aggre['segGroups']:
        aggre_seg_map[segGroup['id']] = list()
        for seg in segGroup['segments']:
            aggre_seg_map[segGroup['id']].extend(seg_map[seg])
    assert(len(aggre_seg_map) == len(aggre['segGroups']))
    # print('num of aggre_seg_map:',len(aggre_seg_map))
            
    ''' Over write label to segments'''
    # vertices = plydata.vertices
    try:
        labels = plydata.metadata['_ply_raw']['vertex']['data']['label']
    except: labels = plydata.elements[0]['label']
    
    instances = np.zeros_like(labels)
    colors = plydata.visual.vertex_colors
    used_vts = set()
    for seg, indices in aggre_seg_map.items():
        s = set(indices)
        if len(used_vts.intersection(s)) > 0:
            raise RuntimeError('duplicate vertex')
        used_vts.union(s)
        for idx in indices:
            instances[idx] = seg

    return plydata, instances

def load_scannet(pth_ply, pth_agg, pth_seg, verbose=False, random_color = False):
    ''' Load GT '''
    plydata = trimesh.load(pth_ply, process=False)        
    num_verts = plydata.vertices.shape[0]
    if verbose:print('num of verts:',num_verts)
    
    ''' Load segment file'''
    with open(pth_seg) as f:
        segs = json.load(f)
    if verbose:print('len(aggre[\'segIndices\']):', len(segs['segIndices']))
    segment_ids = list(np.unique(np.array(segs['segIndices']))) # get unique segment ids
    if verbose:print('num of unique ids:', len(segment_ids))
    
    ''' Load aggregation file'''
    with open(pth_agg) as f:
        aggre = json.load(f)
    # assert(aggre['sceneId'].split('scannet.')[1]==scan_id)
    # assert(aggre['segmentsFile'].split('scannet.')[1] == scan_id+args.segs)

    plydata,instances = scannet_get_instance_ply(plydata, segs, aggre,random_color=random_color )
    
    labels = plydata.metadata['_ply_raw']['vertex']['data']['label'].flatten()
    points = plydata.vertices
    
    # the label is in the range of 1 to 40. 0 is unlabeled
    # instance 0 is unlabeled.
    return plydata, points, labels, instances