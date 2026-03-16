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
 
  ; define allsat grid
  nc2 = addfile("dt_global_allsat_phy_l4.nc", "r")
  lat1d = nc2->latitude
  lon1d = nc2->longitude
  
  opt = True
  opt@ForceOverwrite = True
  rectilinear_to_SCRIP("src_grid.nc", lat1d, lon1d, opt)
  delete(opt)

  ; generate interpolation weights
  opt = True
  opt@InterpMethod = "bilinear"
  opt@ForceOverwrite = True
  opt@SrcRegional = False
  opt@DstRegional = True
  ESMF_regrid_gen_weights("src_grid.nc", "dst_grid.nc", "weights.nc", opt)

  ; perform interpolation
  opt = True

  data_sla_i = nc2->sla
  data_sla_f = data_sla_i*data_sla_i@scale_factor
  data_sla_r = ESMF_regrid_with_weights(data_sla_f, "weights.nc", opt)

  data_err_sla_i = nc2->err_sla
  data_err_sla_f = data_err_sla_i*data_err_sla_i@scale_factor
  data_err_sla_r = ESMF_regrid_with_weights(data_err_sla_f, "weights.nc", opt)

  data_adt_i = nc2->adt
  data_adt_f = data_adt_i*data_adt_i@scale_factor
  data_adt_r = ESMF_regrid_with_weights(data_adt_f, "weights.nc", opt)

  ntstep = dimsizes(nc2->time)
  print(ntstep)

  ; write data to disk
  ofile = "dt_global_allsat_phy_l4_remap.nc"
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
  attr@units = "days since 2011-08-27T00:00:00"
  attr@calendar = "proleptic_gregorian"
  filevarattdef(fout, "time", attr)
  filevardef(fout, "lat_rho", typeof(lat2d), getvardims(lat2d))
  filevarattdef(fout, "lat_rho", lat2d)
  filevardef(fout, "lon_rho", typeof(lon2d), getvardims(lon2d))
  filevarattdef(fout, "lon_rho", lon2d)
  filevardef(fout, "sla", typeof(data_sla_r), (/"time", "eta_rho", "xi_rho"/))
  filevardef(fout, "err_sla", typeof(data_err_sla_r), (/"time", "eta_rho", "xi_rho"/))
  filevardef(fout, "adt", typeof(data_adt_r), (/"time", "eta_rho", "xi_rho"/))

  setfileoption(fout, "DefineMode",False)

  fout->time = (/ ispan(1, ntstep, 1) /)
  fout->lat_rho = (/ lat2d /)
  fout->lon_rho = (/ lon2d /)
  fout->sla = (/ data_sla_r /)  
  fout->err_sla = (/ data_err_sla_r /)  
  fout->adt = (/ data_adt_r /)  
end
