# coding: utf-8

from __future__ import division, print_function

__author__ = "adrn <adrn@astro.columbia.edu>"

# Third-party
import numpy as np

# Project
from ... import potential as gp
from ..nonlinear import lyapunov_max, fast_lyapunov_max, surface_of_section
from ...integrate import DOPRI853Integrator
from ...util import gram_schmidt, atleast_2d
from ...units import galactic

def test_gram_schmidt():
    arr = np.array([
        [0.159947293111244, -0.402071263039210, 0.781989928439469, 0.157200868935014],
        [-0.641365729386551, -0.589502248965056, -6.334333712737469E-002, -0.787834065229250],
        [-0.734648540580147, 0.290410423487680, 0.200395494571665, 0.547331391068177],
        [0.140516164496874, -0.649328455579330, -0.621863558066490, 0.402036027551737]
    ])

    fortran_end_arr = np.array([
        [0.176260247376319, -0.443078334791891, 0.861744738228658, 0.173233716603048],
        [-0.539192290034099, -0.517682965825117, -2.242518016864357E-002, -0.663907472888126],
        [-0.823493801368422, 0.237505395299283, 0.194657453290375, 0.477030001352140],
        [7.871383004849420E-003, -0.692298435168163, -0.467976060614355, 0.549235217994234]
    ])

    alf = gram_schmidt(arr)
    fortran_alf = np.array([0.907449612105405,1.17546413803123,0.974054532627089,0.962464733634354])

    assert np.abs(fortran_alf - alf).sum() < 1E-13
    assert np.abs(arr - fortran_end_arr).sum() < 1E-13

class TestForcedPendulum(object):

    def setup(self):

        def F(t,x,A,omega_d):
            q,p = x
            return np.array([p,-np.sin(q) + A*np.cos(omega_d*t)])

        # initial conditions and parameter choices for chaotic / regular pendulum
        self.regular_w0 = np.array([1.,0.])
        self.regular_par = (0.055, 0.7)
        self.regular_integrator = DOPRI853Integrator(F, func_args=self.regular_par)

        self.chaotic_w0 = np.array([3.,0.])
        self.chaotic_par = (0.07, 0.75)
        self.chaotic_integrator = DOPRI853Integrator(F, func_args=self.chaotic_par)

    def test_lyapunov_max(self, tmpdir):
        nsteps = 20000
        dt = 1.
        nsteps_per_pullback = 10
        d0 = 1e-5
        noffset = 2

        regular_LEs, regular_orbit = lyapunov_max(self.regular_w0, self.regular_integrator,
                                                  dt=dt, nsteps=nsteps,
                                                  d0=d0, nsteps_per_pullback=nsteps_per_pullback,
                                                  noffset_orbits=noffset)

        regular_LEs = np.mean(regular_LEs, axis=1)
        assert regular_LEs[-1] < 1E-3

        chaotic_LEs, chaotic_orbit = lyapunov_max(self.chaotic_w0, self.chaotic_integrator,
                                                  dt=dt, nsteps=nsteps,
                                                  d0=d0, nsteps_per_pullback=nsteps_per_pullback,
                                                  noffset_orbits=noffset)
        chaotic_LEs = np.mean(chaotic_LEs, axis=1)
        assert chaotic_LEs[-1] > 1E-2

        # pl.figure()
        # pl.loglog(regular_LEs, marker=None)
        # pl.savefig(os.path.join(str(tmpdir),"pend_regular.png"))

        # pl.figure()
        # pl.plot(t, regular_ws[:,0], marker=None)
        # pl.savefig(os.path.join(str(tmpdir),"pend_orbit_regular.png"))

        # pl.figure()
        # pl.loglog(chaotic_LEs, marker=None)
        # pl.savefig(os.path.join(str(tmpdir),"pend_chaotic.png"))

        # pl.figure()
        # pl.plot(t, chaotic_ws[:,0], marker=None)
        # pl.savefig(os.path.join(str(tmpdir),"pend_orbit_chaotic.png"))

        # pl.close('all')

# --------------------------------------------------------------------

class HenonHeilesBase(object):

    def potential(self,w,A,B,C,D):
        x,y = w[:2]
        term1 = 0.5*(A*x**2 + B*y**2)
        term2 = D*x**2*y - C/3.*y**3
        return term1 + term2

    def acceleration(self,w,A,B,C,D):
        x,y = w[:2]
        ax = -(A*x + 2*D*x*y)
        ay = -(B*y + D*x*x - C*y*y)
        return np.array([ax, ay])

    def jerk(self,w,A,B,C,D):
        x,y = w[:2]
        dx,dy = w[4:6]

        dax = -(A+2*D*y)*dx - 2*D*x*dy
        day = -2*D*x*dx - (B-2*C*y)*dy

        return np.array([dax,day])

    def F_max(self,t,w,*args):
        x,y,px,py = w
        term1 = np.array([px, py])
        term2 = self.acceleration(w, *args)
        return np.vstack((term1,term2))

    def setup(self):
        # parameter choices
        self.par = (1.,1.,1.,1.)
        self.nsteps = 2000
        self.dt = 2.

    def test_integrate_orbit(self, tmpdir):
        integrator = DOPRI853Integrator(self.F_max, func_args=self.par)

        # pl.clf()
        t,w = integrator.run(self.w0, dt=self.dt, nsteps=self.nsteps)
        # pl.plot(w[:,0,0], w[:,0,1], marker=None)

        # pl.savefig(os.path.join(str(tmpdir),"hh_orbit_{}.png".format(self.__class__.__name__)))

    def test_lyapunov_max(self, tmpdir):
        nsteps_per_pullback = 10
        d0 = 1e-5
        noffset = 2

        integrator = DOPRI853Integrator(self.F_max, func_args=self.par)
        lyap, orbit = lyapunov_max(self.w0, integrator,
                                   dt=self.dt, nsteps=self.nsteps,
                                   d0=d0, noffset_orbits=noffset,
                                   nsteps_per_pullback=nsteps_per_pullback)
        lyap = np.mean(lyap, axis=1)

        # pl.clf()
        # pl.loglog(lyap, marker=None)
        # pl.savefig(os.path.join(str(tmpdir),"hh_lyap_max_{}.png".format(self.__class__.__name__)))

        # pl.clf()
        # pl.plot(ws[...,0], ws[...,1], marker=None)
        # pl.savefig(os.path.join(str(tmpdir),"hh_orbit_lyap_max_{}.png".format(self.__class__.__name__)))

# initial conditions from LP-VI documentation:
class TestHenonHeilesStablePeriodic(HenonHeilesBase):
    def setup(self):
        super(TestHenonHeilesStablePeriodic, self).setup()
        self.w0 = np.array([0.,0.295456,0.407308431,0.])
        self.check = lambda x: x < 1E-3

class TestHenonHeilesStableQuasi1(HenonHeilesBase):
    def setup(self):
        super(TestHenonHeilesStableQuasi1, self).setup()
        self.w0 = np.array([0., 0.483, 0.27898039, 0.])
        self.check = lambda x: x < 2E-3

class TestHenonHeilesStableQuasi2(HenonHeilesBase):
    def setup(self):
        super(TestHenonHeilesStableQuasi2, self).setup()
        self.w0 = np.array([0., 0.46912, 0.291124891, 0.])
        self.check = lambda x: x < 2E-3

class TestHenonHeilesStableChaos1(HenonHeilesBase):
    def setup(self):
        super(TestHenonHeilesStableChaos1, self).setup()
        self.w0 = np.array([0., 0.509, 0.254624859, 0.])
        self.check = lambda x: x > 2E-3

class TestHenonHeilesStableChaos2(HenonHeilesBase):
    def setup(self):
        super(TestHenonHeilesStableChaos2, self).setup()
        self.w0 = np.array([0., 0.56, 0.164113781, 0.112])
        self.check = lambda x: x > 1E-2

# --------------------------------------------------------------------

class TestLogarithmic(object):

    def F(self,t,w):
        x,y,z,px,py,pz = w
        term1 = atleast_2d([px, py, pz], insert_axis=1)
        term2 = self.potential.acceleration(w[:3])
        return np.vstack((term1,term2))

    def setup(self):

        # set the potential
        self.potential = gp.LogarithmicPotential(v_c=np.sqrt(2), r_h=0.1,
                                                 q1=1., q2=0.9, q3=1.,
                                                 units=galactic)

        # see figure 1 from Papaphillipou & Laskar
        x0 = -0.01
        X0 = -0.2
        y0 = 0.
        E0 = -0.4059
        Y0 = np.sqrt(E0 - self.potential.value([x0,y0,0.]))
        chaotic_w0 = [x0,y0,0.,X0,Y0,0.]

        # initial conditions from LP-VI documentation:
        self.w0s = np.array([[0.49, 0., 0., 1.3156, 0.4788, 0.],  # regular
                             chaotic_w0])  # chaotic

        self.nsteps = 25000
        self.dt = 0.004

    def test_fast_lyapunov_max(self, tmpdir):
        nsteps_per_pullback = 10
        d0 = 1e-5
        noffset = 2

        for ii,w0 in enumerate(self.w0s):

            lyap, orbit = fast_lyapunov_max(w0, self.potential,
                                            dt=self.dt, nsteps=self.nsteps,
                                            d0=d0, noffset_orbits=noffset,
                                            nsteps_per_pullback=nsteps_per_pullback)
            lyap = np.mean(lyap, axis=1)

            # also just integrate the orbit to compare dE scaling
            orbit2 = self.potential.integrate_orbit(w0, dt=self.dt, nsteps=self.nsteps,
                                                    Integrator=DOPRI853Integrator)

            # lyapunov exp
            # pl.figure()
            # pl.loglog(lyap, marker=None)
            # pl.savefig(os.path.join(str(tmpdir),"log_lyap_max_{}.png".format(ii)))

            # energy conservation
            E = orbit[:,0].energy().value # returns 3 orbits
            dE = np.abs(E[1:] - E[0])

            E = orbit2.energy().value
            dE_ww = np.abs(E[1:] - E[0])

            assert np.allclose(dE_ww[-100:], dE[-100:], rtol=1E-1)

            # pl.figure()
            # pl.semilogy(dE_ww, marker=None)
            # pl.semilogy(dE, marker=None)
            # pl.show()
            # pl.savefig(os.path.join(str(tmpdir),"log_dE_{}.png".format(ii)))

            # pl.figure(figsize=(6,6))
            # pl.plot(ws[:,0], ws[:,1], marker='.', linestyle='none', alpha=0.1)
            # pl.savefig(os.path.join(str(tmpdir),"log_orbit_lyap_max_{}.png".format(ii)))

    def test_compare_fast(self, tmpdir):
        nsteps_per_pullback = 10
        d0 = 1e-5
        noffset = 2

        integrator = DOPRI853Integrator(self.F)
        for ii,w0 in enumerate(self.w0s):

            lyap1, orbit1 = fast_lyapunov_max(w0, self.potential,
                                              dt=self.dt, nsteps=self.nsteps,
                                              d0=d0, noffset_orbits=noffset,
                                              nsteps_per_pullback=nsteps_per_pullback)
            lyap1 = np.mean(lyap1, axis=1)

            lyap2, orbit2 = lyapunov_max(w0.copy(), integrator,
                                         dt=self.dt, nsteps=self.nsteps,
                                         d0=d0, noffset_orbits=noffset,
                                         nsteps_per_pullback=nsteps_per_pullback,
                                         units=self.potential.units)
            lyap2 = np.mean(lyap2, axis=1)

            # lyapunov exp
            # pl.clf()
            # pl.loglog(t1[1:-10:10], lyap1, marker=None)
            # pl.loglog(t2[1:-10:10], lyap2, marker=None)
            # pl.show()
            # pl.savefig(os.path.join(str(tmpdir),"log_lyap_compare_{}.png".format(ii)))

            # energy conservation
            E = orbit1.energy().value
            dE_fast = np.abs(E[1:] - E[0])
            print(E.shape)

            E = orbit2.energy(self.potential).value
            dE_slow = np.abs(E[1:] - E[0])

            print(E.shape)
            return

            assert np.all(dE_fast < 1E-10)
            assert np.all(dE_slow < 1E-10)

            # pl.clf()
            # pl.semilogy(dE_ww, marker=None)
            # pl.semilogy(dE, marker=None)
            # pl.savefig(os.path.join(str(tmpdir),"log_dE_{}.png".format(ii)))

            # pl.figure(figsize=(6,6))
            # pl.plot(ws[:,0], ws[:,1], marker='.', linestyle='none', alpha=0.1)
            # pl.savefig(os.path.join(str(tmpdir),"log_orbit_lyap_max_{}.png".format(ii)))

def test_surface_of_section(tmpdir):
    # from mpl_toolkits.mplot3d import Axes3D
    from ...potential import LogarithmicPotential
    from ...units import galactic

    pot = LogarithmicPotential(v_c=1., r_h=1., q1=1., q2=0.9, q3=0.8, units=galactic)

    w0 = np.array([[0.,0.8,0.,1.,0.,0.],
                   [0.,0.9,0.,1.,0.,0.]]).T
    orbit = pot.integrate_orbit(w0, dt=0.02, nsteps=100000)
    sos = surface_of_section(orbit, plane_ix=1)

    # plot in 3D
    # fig = pl.figure(figsize=(10,10))
    # ax = fig.add_subplot(111, projection='3d')

    # ax.scatter(np.concatenate(sos[0]), # x
    #            np.concatenate(sos[3]), # xdot
    #            np.concatenate(sos[2]), # z
    #            c=np.concatenate(sos[5])) # zdot
    # ax.set_xlabel('$x$')
    # ax.set_ylabel(r'$\dot{x}$')
    # ax.set_zlabel('$z$')

    # fig.tight_layout()
    # pl.show()
    # fig.savefig(os.path.join("sos.png"))
