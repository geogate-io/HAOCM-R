load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/gsn_code.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/gsn_csm.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/contributed.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/esmf/ESMF_regridding.ncl"
begin
  ; define roms grid
  nc1 = addfile("../run/Data/ROMS/irene_roms_grid.nc", "r")
  lat2d = nc1->lat_rho
  lon2d = nc1->lon_rho  
  dims = dimsizes(lat2d)

  opt = True
  opt@ForceOverwrite = True
  opt@GridMask = nc1->mask_rho
  curvilinear_to_SCRIP("dst_grid.nc", lat2d, lon2d, opt)
  delete(opt)
 
  ; define sst grid
  nc2 = addfile("/glade/work/turuncu/ML/runs/DLROMS/run_cdeps/Data/FRC/era5_IRENE_cdf5.nc", "r")
  lat2dd = nc2->lat
  lon2dd = nc2->lon
  
  opt = True
  opt@ForceOverwrite = True
  curvilinear_to_SCRIP("src_grid.nc", lat2dd, lon2dd, opt)
  delete(opt)

  ; generate interpolation weights
  opt = True
  opt@InterpMethod = "bilinear"
  opt@ForceOverwrite = True
  opt@SrcRegional = True
  opt@DstRegional = True
  ESMF_regrid_gen_weights("src_grid.nc", "dst_grid.nc", "weights.nc", opt)

  ; perform interpolation
  opt = True
  swrad_regrid = ESMF_regrid_with_weights(nc2->swrad, "weights.nc", opt)
  ntstep = dimsizes(nc2->swrad(:,0,0))

  ; write data to disk
  ofile = "roms_era5_remap.nc"
  system("/bin/rm -f "+ofile)
  fout = addfile(ofile, "c")

  setfileoption(fout, "DefineMode", True)

  dimNames = (/"time", "eta_rho", "xi_rho"/)
  dimSizes = (/-1, dims(0), dims(1)/) 
  dimUnlim = (/True , False, False/)
  filedimdef(fout, dimNames, dimSizes, dimUnlim)

  filevardef(fout, "time", typeof(nc2->time), (/ "time" /))
  filevarattdef(fout, "time", nc2->time)
  filevardef(fout, "lat_rho", typeof(lat2d), getvardims(lat2d))
  filevarattdef(fout, "lat_rho", lat2d)
  filevardef(fout, "lon_rho", typeof(lon2d), getvardims(lon2d))
  filevarattdef(fout, "lon_rho", lon2d)
  filevardef(fout, "swrad", typeof(swrad_regrid), (/"time", "eta_rho", "xi_rho"/))
  filevarattdef(fout, "swrad", nc2->swrad)

  setfileoption(fout, "DefineMode",False)

  print(nc2->time)
  fout->time = (/ nc2->time /)
  fout->lat_rho = (/ lat2d /)
  fout->lon_rho = (/ lon2d /)
  fout->swrad = (/ swrad_regrid /)  
end
