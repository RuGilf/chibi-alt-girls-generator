"""One shared spatial field for body, clothing, accessories, and armature rest pose."""
import numpy as np
GROUND=.018
HEAD_PIVOT=1.225

def smooth(lo,hi,z):
    t=np.clip((z-lo)/(hi-lo),0,1);return t*t*(3-2*t)

def deform(points,body,part='body'):
    """Input/output: neutral character coordinates, independent of root placement."""
    p=np.array(points,dtype=np.float64,copy=True).reshape(-1,3)
    x,y,z=p[:,0].copy(),p[:,1].copy(),p[:,2].copy()
    if part=='leg':
        side=np.where(x>=0,1.,-1.)
        center=np.interp(z,[.20,.40,.51,.62,.75],[.105,.102,.097,.091,.082])*side
        thigh=np.exp(-((z-.64)/.18)**2)
        calf=np.exp(-((z-.405)/.145)**2)
        # Shoe toe length and sole position stay stable; shaft width follows the calf.
        limb=smooth(.13,.25,z)
        scale=1+limb*((body['thigh_size']-.5)*.70*thigh+(body['calf_size']-.5)*.46*calf+side*body['leg_asymmetry'])
        x=center+(x-center)*scale
        y=y*(1+(scale-1)*.84)
    elif part in ('skirt','hip'):
        hip=1+(body['thigh_size']-.5)*.15
        x*=hip;y*=hip
    # Garments use the same field as the body. Front is -Y; back is +Y.
    # Keep shoulders, neck, waist, hands and footwear outside these volume fields.
    if part in ('body','hip','skirt','leg'):
        if part=='body':
            front=smooth(.008,.075,-y)
            chest_z=np.exp(-((z-1.085)/.079)**2)*smooth(.965,1.015,z)*(1-smooth(1.165,1.215,z))
            twin=np.exp(-((np.abs(x)-.065)/.064)**2)
            y-=body.get('breast_size',0.0)*.10*chest_z*twin*front
        back=smooth(.015,.095,y)
        glute_z=np.exp(-((z-.805)/.084)**2)*smooth(.665,.725,z)*(1-smooth(.875,.93,z))
        width=np.exp(-((np.abs(x)-.090)/.095)**2)
        volume=body.get('glute_size',.5)-.5
        amount=volume*(.04 if volume<0 else .11)
        if part=='skirt':
            # A pleated skirt drapes from the hips and keeps an open hem.
            # It must not cling back inward below the fullest point.
            drape=(.80+.20*smooth(.67,.80,z))*(1-smooth(.865,.94,z))*smooth(.62,.65,z)
            y+=amount*drape*width*back
        else:y+=amount*glute_z*width*back
        x+=np.sign(x)*(body.get('glute_size',.5)-.5)*.024*glute_z*smooth(.04,.15,np.abs(x))
    # Very mild S-shaped centerline; the head above the pivot moves as a rigid unit.
    amp=.018*body['curve_severity']*body['curve_direction']
    lo=.775;length=HEAD_PIVOT-lo;t=np.clip((z-lo)/length,0,1)
    curve=amp*(np.sin(2*np.pi*t)*np.sin(np.pi*t)+.4*t*t)
    derivative=amp/length*(2*np.pi*np.cos(2*np.pi*t)*np.sin(np.pi*t)+np.pi*np.sin(2*np.pi*t)*np.cos(np.pi*t)+.8*t)
    theta=np.clip(derivative,-.055,.055)+body['shoulder_tilt']*smooth(.84,1.17,z)
    theta=np.where(z<lo,0,theta)
    neck_angle=amp*.8/length+body['shoulder_tilt']
    above=z>HEAD_PIVOT
    xcurve=np.where(above,.4*amp+np.sin(neck_angle)*(z-HEAD_PIVOT),curve)
    angle=np.where(above,neck_angle,theta)
    xx=x*np.cos(angle)+xcurve
    zz=np.where(above,HEAD_PIVOT+np.cos(neck_angle)*(z-HEAD_PIVOT),z)-x*np.sin(angle)
    # Height changes mostly the body; the expressive head remains almost the same size.
    height=1+(body['height']-.5)*.34
    head_scale=1+(body['height']-.5)*.035
    pivot_new=GROUND+(HEAD_PIVOT-GROUND)*height
    zz=np.where(zz<=HEAD_PIVOT,GROUND+(zz-GROUND)*height,pivot_new+(zz-HEAD_PIVOT)*head_scale)
    p[:,0]=xx;p[:,1]=y;p[:,2]=zz
    return p
