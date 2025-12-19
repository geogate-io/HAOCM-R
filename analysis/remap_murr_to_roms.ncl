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
  nc2 = addfile("sst_murr_2011-08-21_2011-08-30.nc", "r")
  lat1d = nc2->lat
  lon1d = nc2->lon 
  
  opt = True
  opt@ForceOverwrite = True
  rectilinear_to_SCRIP("src_grid.nc", lat1d, lon1d, opt)
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
  sst_regrid = ESMF_regrid_with_weights(nc2->analysed_sst, "weights.nc", opt)
  ntstep = dimsizes(nc2->analysed_sst(:,0,0))

  ; write data to disk
  ofile = "sst_murr_2011-08-21_2011-08-30_remap.nc"
  system("/bin/rm -f "+ofile)
  fout = addfile(ofile, "c")

  setfileoption(fout, "DefineMode", True)

  dimNames = (/"time", "eta_rho", "xi_rho"/)
  dimSizes = (/-1, dims(0), dims(1)/) 
  dimUnlim = (/True , False, False/)
  filedimdef(fout, dimNames, dimSizes, dimUnlim)

  filevardef(fout, "time", "integer", (/ "time" /))
  attr = True
  attr@standard_name = "time"
  attr@units = "days since 2011-08-21T00:00:00"
  attr@calendar = "proleptic_gregorian"
  filevarattdef(fout, "time", attr)
  filevardef(fout, "lat_rho", typeof(lat2d), getvardims(lat2d))
  filevarattdef(fout, "lat_rho", lat2d)
  filevardef(fout, "lon_rho", typeof(lon2d), getvardims(lon2d))
  filevarattdef(fout, "lon_rho", lon2d)
  filevardef(fout, "analysed_sst", typeof(sst_regrid), (/"time", "eta_rho", "xi_rho"/))
  filevarattdef(fout, "analysed_sst", nc2->analysed_sst)

  setfileoption(fout, "DefineMode",False)

  fout->time = (/ ispan(1, ntstep, 1) /)
  fout->lat_rho = (/ lat2d /)
  fout->lon_rho = (/ lon2d /)
  fout->analysed_sst = (/ sst_regrid /)  
end
