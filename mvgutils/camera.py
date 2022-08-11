# AUTOGENERATED! DO NOT EDIT! File to edit: ../03_camera.ipynb.

# %% auto 0
__all__ = ['COLMAP_CAMERA_MODELS', 'print_supported_camera_models', 'CameraIntrinsicts']

# %% ../03_camera.ipynb 3
import numpy as np
from easydict import EasyDict as edict

# %% ../03_camera.ipynb 5
COLMAP_CAMERA_MODELS = dict(
    SIMPLE_PINHOLE = dict(id=0, n_params=3, params_str='f, cx, cy'), 
    PINHOLE        = dict(id=1, n_params=4,params_str='fx, fy, cx, cy'), 
    SIMPLE_RADIAL  = dict(id=2, n_params=4,params_str='f, cx, cy, k'), 
    RADIAL         = dict(id=3, n_params=5,params_str='f, cx, cy, k1, k2'), 
    OPENCV         = dict(id=4, n_params=8,params_str='fx, fy, cx, cy, k1, k2, p1, p2'), 
    OPENCV_FISHEYE = dict(id=5, n_params=8,params_str='fx, fy, cx, cy, k1, k2, k3, k4'), 
    FULL_OPENCV    = dict(id=6, n_params=12,params_str='fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, k5, k6'), 
    FOV            = dict(id=7, n_params=5,params_str='fx, fy, cx, cy, omega'), 
    OPENCV5        = dict(id=-1, n_params=9,params_str='fx, fy, cx, cy, k1, k2, p1, p2, k3'),
    UNKNOWN        = dict(id=-1, n_params=0,params_str='[]'), 
)

def print_supported_camera_models():
    print('List of supported camera models and their parameters')
    print(55*'_')
    for m in COLMAP_CAMERA_MODELS:
        p = COLMAP_CAMERA_MODELS[m]['params_str']
        print(f'{m:20}: {p}')


# %% ../03_camera.ipynb 7
class CameraIntrinsicts:
    'Camera intrinsic model'
    def __init__(self, 
                 camera_model_name: str,   # One of the keys in COLMAP_CAMERA_MODELS
                 width: int,               # width of the image in pixels
                 height: int,              # height of the image in pixels
                 params: list):            # parameters, in COLMAP conventions
        # prior_focal_length : 1 if we have confidence in the modelparameters and 0 if we do not trust the model parameters

        if camera_model_name not in COLMAP_CAMERA_MODELS:
            raise ValueError(f'Camera model ["{camera_model_name}"] not recognized as colmap camera model')
        
        param_names = COLMAP_CAMERA_MODELS[camera_model_name]['params_str'].split(',')
        param_names = [p.strip() for p in param_names]
        if len(param_names) != len(params):
            raise ValueError(f'{camera_model_name} expectes {len(param_names)} parameters but got {len(params)}') 

        self._w = width
        self._h = height

        self.camera_model_name = camera_model_name
        self._set_params(camera_model_name, params)
            
    def __str__(self):
        s  = f'Camera: {self.camera_model_name}\n'
        s += f'  w,h={self.width,self.height}\n'
        s += f'  params: {self.params}\n'
        s += f'  cx,cy= ({self.cx},{self.cy})\n'
        s += f'  fx,fy= ({self.fx},{self.fy})\n'
        s += f'  distortions: {self._D}\n'


        return s

    __repr__ = __str__
            
    @property 
    def w(self):
        return self._w

    @property 
    def width(self):
        return self._w

    @property 
    def h(self):
        return self._h

    @property 
    def height(self):
        return self._h


    def K(self, use_homogenous_coordinates=True):
        K_mat = np.array(
            [
                [self.fx, 0.0,     self.cx, 0.0],
                [0.0,     self.fy, self.cy, 0.0],
                [0.0,     0.0,     1.0,     0.0 ],
                [0.0,     0.0,     0.0,     1.0 ]
            ]
        )

        if not use_homogenous_coordinates:
            return K_mat[:3,:3]
        return K_mat

    @property
    def distortions(self):
        return np.array(self._D)

    @staticmethod
    def from_pinhole_model(fx: float, fy: float, cx:float, cy: float, width: int, height: int):
        if fx == fy:
            camera_model_name = 'SIMPLE_PINHOLE'
            params = [fx, cx, cy]
        else:
            camera_model_name = 'PINHOLE'
            params = [fx, fy, cx, cy]

        return CameraIntrinsicts(camera_model_name,width, height, params)

    @staticmethod
    def from_opencv_model(K: np.ndarray, # 3x3 camera matrix
                          distortions: np.ndarray, # distortion array as produced by OpenCv
                          width: int, # Camera width in pixels
                          height: int # Camera height in pixels
                         ) -> 'CameraIntrinsicts':
        'Contructing camera intrinsics model from opencv compatible data'
        if not isinstance(distortions, list):
            if len(distortions.shape) == 2:
                distortions = distortions.squeeze()
            distortions= distortions.tolist()
     
        fx = K[0,0]
        cx = K[0,2]
        fy = K[1,1]
        cy = K[1,2]

        params = [fx, fy, cx, cy]
        if len(distortions) == 4:
            camera_model_name = 'OPENCV'
            params += distortions
        elif len(distortions) == 5:
            camera_model_name = 'OPENCV5'
            params += distortions
        else:
            raise ValueError(f'Do not support opencv model with {len(distortions)} parameters')

        return CameraIntrinsicts(camera_model_name,width, height, params)

    def get_undistort_matrix(self, alpha=1.0):
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(self.K, self.distortions, (self.w,self.h), alpha, (self.w,self.h))
        return newcameramtx

    def _set_params(self, camera_model_name, params):
        param_names = COLMAP_CAMERA_MODELS[camera_model_name]['params_str'].split(',')
        param_names = [p.strip() for p in param_names]
        if len(param_names) != len(params):
            raise ValueError(f'{camera_model_name} expectes {len(param_names)} parameters but got {len(params)}') 

        self._params = params
        
        # First names should be one of f,fx,fy,cx,cy
        camera_matrix_components = ['f','fx','fy','cx','cy']
        self._D = []
        for i, (name, val) in enumerate(zip(param_names,params)):
#             print(name,val)
            if name not in camera_matrix_components:
                self._D.append(val)
            if name == 'f': 
                self.fx = self.fy = val
            else:
                setattr(self, name, val)
             

    
    def _get_params_to_new_cx_cy_fx_fy(self, new_cx, new_cy, new_fx=None, new_fy=None):
        new_fx = self.fx if new_fx is None else new_fx
        new_fy = self.fy if new_fy is None else new_fy

        params = copy.deepcopy(self._params)
        camera_model_name = self.camera_model_name
        if camera_model_name == 'SIMPLE_PINHOLE':
            params[0] = new_fx
            params[1] = new_cx
            params[2] = new_cy
        elif camera_model_name == 'PINHOLE':
            params[0] = new_fx
            params[1] = new_fy
            params[2] = new_cx
            params[3] = new_cy
        elif camera_model_name == 'SIMPLE_RADIAL':
            params[0] = new_fx
            params[1] = new_cx
            params[2] = new_cy
        elif camera_model_name == 'RADIAL':
            params[0] = new_fx
            params[1] = new_cx
            params[2] = new_cy
        elif camera_model_name == 'OPENCV':
            params[0] = new_fx
            params[1] = new_fy
            params[2] = new_cx
            params[3] = new_cy
        elif camera_model_name == 'OPENCV_FISHEYE':
            params[0] = new_fx
            params[1] = new_fy
            params[2] = new_cx
            params[3] = new_cy
        elif camera_model_name == 'FULL_OPENCV':
            params[0] = new_fx
            params[1] = new_fy
            params[2] = new_cx
            params[3] = new_cy
        elif camera_model_name == 'FOV':
            params[0] = new_fx
            params[1] = new_fy
            params[2] = new_cx
            params[3] = new_cy
        else:
            raise(f'This should not happen')

        return params

    def crop_bbox(self, in_bbox, c_bbox, new_width, new_height):
        if in_bbox is None: return None

        if in_bbox.minx >= c_bbox.maxx or in_bbox.maxx <= c_bbox.minx: return None
        if in_bbox.miny >= c_bbox.maxy or in_bbox.maxy <= c_bbox.miny: return None

        b_xmin = max(in_bbox.minx - c_bbox.minx,0)
        b_xmax = min(max(in_bbox.maxx - c_bbox.minx,0), new_width)
        b_ymin = max(in_bbox.miny - c_bbox.miny,0)
        b_ymax = min(max(in_bbox.maxy - c_bbox.miny,0), new_height)
        if b_xmin == b_xmax or b_ymin == b_ymax: return None

        return edict(
            minx = b_xmin,
            maxx = b_xmax,
            miny = b_ymin,
            maxy = b_ymax
        )
    
    @property
    def params(self):
        return self._params


    def resize(self, new_size):
        """Change camera intrinsicts due to image resize --> scale of focal lenghts
        Args:
            new_size (tuple): (destination_width, destination_height)
        """
        new_width = new_size[0]
        new_height = new_size[1]
        scale_w = new_width / self.width
        scale_h = new_height / self.height

        fx  = self.fx * scale_w    # fx
        cx  = self.cx * scale_w    # cx
        fy  = self.fy * scale_h    # fy
        cy  = self.cy * scale_h    # cy

        new_params = self._get_params_to_new_cx_cy_fx_fy(cx, cy, fx, fy)

        return CameraIntrinsicts(
            camera_model_name=self.camera_model_name, 
            width=new_width, 
            height=new_height, 
            params=new_params
        )

    def crop(self, bbox, new_name=None):
        """Change camera intrinsicts due to clipping to a rectangular window --> shifting the proincipal point
        Args:
            min_crop_x (float): Minimal coordinate of clipping rectangle in x directior, in pixels
            min_crop_y ([float]): Minimal coordinate of clipping rectangle in y directior, in pixels
        """
        new_cx = self.cx -  int(round(bbox.minx))   # cx
        new_cy = self.cy - int(round(bbox.miny))   # cy

        new_width = bbox.maxx - bbox.minx
        new_height = bbox.maxy - bbox.miny

        new_params = self._get_params_to_new_cx_cy_fx_fy(new_cx, new_cy)

        return CameraIntrinsicts(
            camera_model_name=self.camera_model_name, 
            width=new_width, 
            height=new_height, 
            params=new_params
        )

    def get_optimal_new_camera_matrix(self, alpha):
        """_summary_

        Args:
            alpha (float): A number between 0 and 1, If the value is 
               alpha = 0 --> when all the pixels in the undistorted image are valid
               alpha = 1 --> when all the source image pixels are retained in the undistorted image but with many black pixels 
            new_image_size (_type_, optional): _description_. Defaults to None.
        """
        # See cvGetOptimalNewCameraMatrix in line 2714 of https://github.com/opencv/opencv/blob/4.x/modules/calib3d/src/calibration.cpp
        # See https://docs.opencv.org/3.3.0/dc/dbb/tutorial_py_calibration.html

        outer, inner = self.icv_get_rectangles()

        new_image_width = self.width
        new_image_height = self.height
   
        # Projection mapping inner rectangle to viewport
        fx0 = (new_image_width-1)/ inner.width
        fy0 = (new_image_height-1)/ inner.height
        cx0 = -fx0 * inner.x
        cy0 = -fy0 * inner.y

        # Projection mapping outer rectangle to viewport
        fx1 = (new_image_width-1)/ outer.width
        fy1 = (new_image_height-1)/ outer.height
        cx1 = -fx1 * outer.x
        cy1 = -fy1 * outer.y

        # Interpolate between the two optimal projections
        fx = fx0*(1 - alpha) + fx1*alpha
        fy = fy0*(1 - alpha) + fy1*alpha
        cx = cx0*(1 - alpha) + cx1*alpha
        cy = cy0*(1 - alpha) + cy1*alpha

        new_params = [fx,fy,cx,cy]
        return CameraIntrinsicts(
            camera_model_name='PINHOLE', 
            width=new_image_width, 
            height=new_image_height, 
            params=new_params
        )



    def project_camera_plane_to_image_plane(self, pc: np.array):
        K = self.K(use_homogenous_coordinates=False)
        fx = K[0,0]
        fy = K[1,1]
        cx = K[0,2]
        cy = K[1,2]
        x_pix = fx*pc[0] + cx
        y_pix = fy*pc[1] + cy
        return np.array([x_pix, y_pix])

    def project_image_plane_to_camera_plane(self, pu: np.array):
        K = self.K(use_homogenous_coordinates=False)
        fx = K[0,0]
        fy = K[1,1]
        cx = K[0,2]
        cy = K[1,2]
        
        xc = (pu[0] - cx)/fx
        yc = (pu[1] - cy)/fy
        return np.array([xc, yc])

    def undistort(self, pc_distorted: np.array):
        # see line 565 in https://github.com/colmap/colmap/blob/dev/src/base/camera_models.h
        eps =np.finfo(np.float64).eps

        kNumIterations = 100
        kMaxStepNorm = np.float32(1e-10)
        kRelStepSize = np.float32(1e-6)

        J = np.eye(2)
        x0 = pc_distorted.copy()
        x = pc_distorted.copy()
        for i in range(kNumIterations):
            step0 = np.max([eps, kRelStepSize * x[0]])
            step1 = np.max([eps, kRelStepSize * x[1]])

            dx = self.distort(x)

            dx_0b = self.distort(np.array([x[0] - step0, x[1]]))
            dx_0f = self.distort(np.array([x[0] + step0, x[1]]))
            dx_1b = self.distort(np.array([x[0]        , x[1] - step1]))
            dx_1f = self.distort(np.array([x[0]        , x[1] + step1]))
            J[0, 0] = 1 + (dx_0f[0] - dx_0b[0]) / (2 * step0)
            J[0, 1] = (dx_1f[0] - dx_1b[0]) / (2 * step1)
            J[1, 0] = (dx_0f[1] - dx_0b[1]) / (2 * step0)
            J[1, 1] = 1 + (dx_1f[1] - dx_1b[1]) / (2 * step1)
    
            step_x = np.linalg.inv(J) @ (dx - x0)
            x -= step_x

            squaren_norm = step_x[0]*step_x[0] + step_x[1]*step_x[1]
            if squaren_norm < kMaxStepNorm:
                break

        return  x   # undistorted


    def distort(self, p_cam_distorted: np.array):
        # see line 888 in https://github.com/colmap/colmap/blob/dev/src/base/camera_models.h
        camera_model_name = self.camera_model_name
        distortions = self.distortions

        if camera_model_name == 'SIMPLE_PINHOLE' or camera_model_name == 'PINHOLE':
            p_cam_undistorted =  p_cam_distorted.copy()

        if camera_model_name == 'OPENCV5':
            # See https://learnopencv.com/understanding-lens-distortion/
            k1 = distortions[0]
            k2 = distortions[1]
            p1 = distortions[2]
            p2 = distortions[3] 
            k3 = distortions[4]

            xd = p_cam_distorted[0]
            yd = p_cam_distorted[1]

            x2 = xd*xd
            y2 = yd*yd
            xy = xd*yd
            r2 = x2 + y2
            r4 = r2*r2
            r6 = r2*r4

            a = 1.0 + k1*r2  + k2*r4 + k3*r6
            xu = a*xd + 2.0*p1*xy + p2*(r2 + 2.0*x2)
            yu = a*yd + p1*(r2+2.0*y2) + 2.0*p2*xy
    
        p_cam_distorted = np.array([xu,yu])

        return p_cam_distorted

    def icv_get_rectangles(self):
        # see icvGetRectangles, line 2460 in https://github.com/opencv/opencv/blob/4.x/modules/calib3d/src/calibration.cpp
        N = 9
        x_step = self.w / (N-1)
        y_step = self.h / (N-1)

        # Get a grid over [w,h] image in original, distorted, coordinates
        xu = []
        yu = []
        xu_left = []
        xu_right = []
        yu_bottom = [] 
        yu_top = []         
        for y in range(N):
            yp = y*y_step
            for x in range(N):
                xp = x*x_step
                ps = np.array([xp,yp])
                pc_distorted = self.project_image_plane_to_camera_plane(ps)                # from 2d pixel coordinates to 2D camera plane
                pc_undistorted = self.undistort(pc_distorted)                              # undistors with inverse lens distortions

                x_undistorted = pc_undistorted[0]
                y_undistorted = pc_undistorted[1]

                xu.append(x_undistorted)
                yu.append(y_undistorted)
                if x == 0: xu_left.append(x_undistorted)
                if x == N-1: xu_right.append(x_undistorted)
                if y == 0: yu_top.append(y_undistorted)
                if y == N-1: yu_bottom.append(y_undistorted)


        xmin_o = np.min(xu)
        xmax_o = np.max(xu)
        ymin_o = np.min(yu)
        ymax_o = np.max(yu)
        outer = edict(x=xmin_o, y=ymin_o, width=xmax_o-xmin_o, height=ymax_o-ymin_o)


        xmin_i = np.max(xu_left)
        xmax_i = np.min(xu_right)
        ymin_i = np.max(yu_top)
        ymax_i = np.min(yu_bottom)
        inner = edict(x=xmin_i, y=ymin_i, width=xmax_i-xmin_i, height=ymax_i-ymin_i)

        return outer, inner

    def get_fov(self):
        # Zeliltsky 2.60
        fovx = 2 * np.rad2deg(np.arctan2(self.width , (2 * self.fx)))
        fovy = 2 * np.rad2deg(np.arctan2(self.height , (2 * self.fy)))

        return edict(fovx=fovx, fovy=fovy)

    def to_dict(self):
        return self.as_dict()

    def as_dict(self):
        asdict = dict(
            width=self.width,
            height=self.height,
            camera_model_name=self.camera_model_name,
            params=[float(p) for p in self.params.tolist()]
        )
        return asdict

#     def to_json(self, json_file):
#         write_json_file(self.as_dict(), json_file)

