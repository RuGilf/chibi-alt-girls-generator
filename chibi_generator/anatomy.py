"""Shared neutral limb profiles and smooth arm weights for skin and clothing."""
import numpy as np
REVISION=1
ARM_PROFILE=[(.162,.005,1.165,.038),(.190,.005,1.151,.040),
             (.211,.005,1.130,.038),(.244,.003,1.066,.032),
             (.254,.002,1.030,.030),(.277,-.004,.977,.033),
             (.291,-.010,.915,.028),(.302,-.015,.862,.024),
             (.307,-.014,.836,.026)]
LEG_PROFILE=[(.105,0,.12,.043,.046),(.105,0,.20,.047,.049),
             (.105,0,.28,.048,.049),(.102,0,.40,.051,.051),
             (.099,-.001,.465,.054,.052),(.097,-.002,.51,.053,.053),
             (.094,0,.565,.058,.056),(.091,0,.62,.062,.060),
             (.082,0,.75,.071,.067)]

def smooth(lo,hi,value):
    t=np.clip((value-lo)/(hi-lo),0,1);return t*t*(3-2*t)

def profile(points,steps=6):
    """Catmull-Rom samples with clamped ends; shared by skin and garment profiles."""
    p=np.asarray(points,dtype=float);result=[]
    for i in range(len(p)-1):
        a,b,c,d=p[max(0,i-1)],p[i],p[i+1],p[min(len(p)-1,i+2)]
        for j in range(steps):
            t=j/steps;result.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return np.asarray(result+[p[-1]])

def arm_weights(points):
    """Columns: clavicle, upper arm, forearm, hand. Sum is exactly one."""
    p=np.array(points,copy=True);p[:,0]=np.abs(p[:,0])
    joints=np.array([(.025,0,1.19),(.175,0,1.176),(.254,.002,1.03),(.302,-.015,.86),(.309,-.015,.785)])
    distances=[]
    for a,b in zip(joints,joints[1:]):
        d=b-a;t=np.clip(((p-a)@d)/(d@d),0,1)
        distances.append(np.linalg.norm(p-a-t[:,None]*d,axis=1))
    distances=np.stack(distances,axis=1);weights=np.exp(-100*(distances-distances.min(axis=1)[:,None]));weights/=weights.sum(axis=1)[:,None]
    blend=smooth(.840,.90,p[:,2]);weights*=blend[:,None];weights[:,3]+=1-blend
    return weights
