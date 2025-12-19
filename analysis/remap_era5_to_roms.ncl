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
  print("dst grid is defined")
 
  ; define sst grid
  nc2 = addfile("merged_1h_with_humidity_sub.nc", "r")
  lat1d = nc2->latitude
  lon1d = nc2->longitude
  
  opt = True
  opt@ForceOverwrite = True
  rectilinear_to_SCRIP("src_grid.nc", lat1d, lon1d, opt)
  delete(opt)
  print("src grid is defined")

  ; generate interpolation weights
  opt = True
  opt@InterpMethod = "bilinear"
  opt@ForceOverwrite = True
  opt@SrcRegional = True
  opt@DstRegional = True 
  ESMF_regrid_gen_weights("src_grid.nc", "dst_grid.nc", "weights.nc", opt)
  print("weight is generated")

  ; write data to disk
  ofile = "merged_1h_with_humidity_sub_remap.nc"
  system("/bin/rm -f "+ofile)
  fout = addfile(ofile, "c")

  setfileoption(fout, "DefineMode", True)

  dimNames = (/"time", "eta_rho", "xi_rho"/)
  dimSizes = (/-1, dims(0), dims(1)/)
  dimUnlim = (/True , False, False/)
  filedimdef(fout, dimNames, dimSizes, dimUnlim)

  filevardef(fout, "time", "double", (/ "time" /))
  filevarattdef(fout, "time", nc2->time)
  filevardef(fout, "lat_rho", typeof(lat2d), getvardims(lat2d))
  filevarattdef(fout, "lat_rho", lat2d)
  filevardef(fout, "lon_rho", typeof(lon2d), getvardims(lon2d))
  filevarattdef(fout, "lon_rho", lon2d)
  var_list = getfilevarnames(nc2)
  do i = 0, dimsizes(var_list)-1
     if (.not. any(var_list(i) .eq. (/ "u", "v", "t", "q", "z", "time", "level", "latitude", "longitude" /))) then
        if (any(var_list(i) .eq. (/ "hgt", "lsm", "slt" /))) then
           filevardef(fout, var_list(i), typeof(nc2->$var_list(i)$), (/"eta_rho", "xi_rho"/))
        else
           filevardef(fout, var_list(i), typeof(nc2->$var_list(i)$), (/"time", "eta_rho", "xi_rho"/))
        end if
        filevarattdef(fout, var_list(i), nc2->$var_list(i)$)
     end if
  end do

  setfileoption(fout, "DefineMode",False)

  fout->time = (/ nc2->time /)
  fout->lat_rho = (/ lat2d /)
  fout->lon_rho = (/ lon2d /)

  ; perform interpolation
  var_list = getfilevarnames(nc2)
  do i = 0, dimsizes(var_list)-1
     if (.not. any(var_list(i) .eq. (/ "u", "v", "t", "q", "z", "time", "level", "latitude", "longitude" /))) then
        opt = True
        var = ESMF_regrid_with_weights(nc2->$var_list(i)$, "weights.nc", opt)
        fout->$var_list(i)$ = (/ var /)
        delete(var)
     end if
  end do
end
