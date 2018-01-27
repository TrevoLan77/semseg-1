#!/usr/bin/python
# -*- coding: UTF-8 -*-
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
from torchvision import models

class conv2DBatchNorm(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size,  stride, padding, bias=True):
        super(conv2DBatchNorm, self).__init__()

        self.cb_seq = nn.Sequential(
            nn.Conv2d(int(in_channels), int(out_channels), kernel_size=kernel_size, padding=padding, stride=stride, bias=bias),
            nn.BatchNorm2d(int(out_channels)),
        )

    def forward(self, inputs):
        outputs = self.cb_seq(inputs)
        return outputs

class conv2DBatchNormRelu(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, padding, bias=True, dilation=1):
        super(conv2DBatchNormRelu, self).__init__()
        self.cbr_seq = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=kernel_size, stride=stride, padding=padding, bias=bias, dilation=dilation),
            nn.BatchNorm2d(num_features=out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        x = self.cbr_seq(x)
        return x

class unetDown(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(unetDown, self).__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=0),
            nn.BatchNorm2d(num_features=out_channels),
            nn.ReLU(inplace=True),
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(in_channels=out_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=0),
            nn.BatchNorm2d(num_features=out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        return x

class unetUp(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(unetUp, self).__init__()
        self.upConv = nn.ConvTranspose2d(in_channels=in_channels, out_channels=out_channels, kernel_size=2, stride=2)
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=0),
            nn.ReLU(inplace=True),
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(in_channels=out_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=0),
            nn.ReLU(inplace=True),
        )


    def forward(self, x_cur, x_prev):
        x = self.upConv(x_cur)
        x = torch.cat([F.upsample_bilinear(x_prev, size=x.size()[2:]), x], 1)
        x = self.conv1(x)
        x = self.conv2(x)
        return x


class segnetDown2(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(segnetDown2, self).__init__()
        self.conv1 = conv2DBatchNormRelu(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.conv2 = conv2DBatchNormRelu(in_channels=out_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.max_pool = nn.MaxPool2d(kernel_size=2, stride=2, return_indices=True)
        pass

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        unpool_shape = x.size()
        # print(unpool_shape)
        x, pool_indices = self.max_pool(x)
        return x, pool_indices, unpool_shape


class segnetDown3(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(segnetDown3, self).__init__()
        self.conv1 = conv2DBatchNormRelu(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.conv2 = conv2DBatchNormRelu(in_channels=out_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.conv3 = conv2DBatchNormRelu(in_channels=out_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.max_pool = nn.MaxPool2d(kernel_size=2, stride=2, return_indices=True)
        pass

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        unpool_shape = x.size()
        # print(unpool_shape)
        x, pool_indices = self.max_pool(x)
        return x, pool_indices, unpool_shape


class segnetUp2(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(segnetUp2, self).__init__()
        self.max_unpool = nn.MaxUnpool2d(kernel_size=2, stride=2)
        self.conv1 = conv2DBatchNormRelu(in_channels=in_channels, out_channels=in_channels, kernel_size=3, stride=1, padding=1)
        self.conv2 = conv2DBatchNormRelu(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        pass

    def forward(self, x, pool_indices, unpool_shape):
        x = self.max_unpool(x, indices=pool_indices, output_size=unpool_shape)
        x = self.conv1(x)
        x = self.conv2(x)
        return x


class segnetUp3(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(segnetUp3, self).__init__()
        self.max_unpool = nn.MaxUnpool2d(kernel_size=2, stride=2)
        self.conv1 = conv2DBatchNormRelu(in_channels=in_channels, out_channels=in_channels, kernel_size=3, stride=1, padding=1)
        self.conv2 = conv2DBatchNormRelu(in_channels=in_channels, out_channels=in_channels, kernel_size=3, stride=1, padding=1)
        self.conv3 = conv2DBatchNormRelu(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        pass

    def forward(self, x, pool_indices, unpool_shape):
        x = self.max_unpool(x, indices=pool_indices, output_size=unpool_shape)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        return x

class residualBlock(nn.Module):
    expansion = 1

    def __init__(self, in_channels, out_channels, stride=1, downsample=None):
        super(residualBlock, self).__init__()

        self.convbnrelu1 = conv2DBatchNormRelu(in_channels, out_channels, 3,  stride, 1, bias=False)
        self.convbn2 = conv2DBatchNorm(out_channels, out_channels, 3, 1, 1, bias=False)
        self.downsample = downsample
        self.stride = stride
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        residual = x

        out = self.convbnrelu1(x)
        out = self.convbn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)
        return out

class linknetUp(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(linknetUp, self).__init__()

        # B, 2C, H, W -> B, C/2, H, W
        self.convbnrelu1 = conv2DBatchNormRelu(in_channels, out_channels/2, kernel_size=1, stride=1, padding=1)

        # B, C/2, H, W -> B, C/2, H, W
        self.deconvbnrelu2 = deconv2DBatchNormRelu(out_channels/2, out_channels/2, kernel_size=3,  stride=2, padding=0,)

        # B, C/2, H, W -> B, C, H, W
        self.convbnrelu3 = conv2DBatchNormRelu(out_channels/2, out_channels, kernel_size=1, stride=1, padding=1)

    def forward(self, x):
        x = self.convbnrelu1(x)
        x = self.deconvbnrelu2(x)
        x = self.convbnrelu3(x)
        return x

class deconv2DBatchNormRelu(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, padding, bias=True):
        super(deconv2DBatchNormRelu, self).__init__()

        self.dcbr_unit = nn.Sequential(nn.ConvTranspose2d(int(in_channels), int(out_channels), kernel_size=kernel_size,
                                                padding=padding, stride=stride, bias=bias),
                                 nn.BatchNorm2d(int(out_channels)),
                                 nn.ReLU(inplace=True),)

    def forward(self, inputs):
        outputs = self.dcbr_unit(inputs)
        return outputs


class bottleNeckIdentifyPSP(nn.Module):
    def __init__(self, in_channels, mid_channels, stride, dilation=1):
        super(bottleNeckIdentifyPSP, self).__init__()

        self.cbr1 = conv2DBatchNormRelu(in_channels, mid_channels, 1, 1, 0, bias=False)
        if dilation > 1:
            self.cbr2 = conv2DBatchNormRelu(mid_channels, mid_channels, 3, 1,
                                            padding=dilation, bias=False,
                                            dilation=dilation)
        else:
            self.cbr2 = conv2DBatchNormRelu(mid_channels, mid_channels, 3,
                                            stride=1, padding=1,
                                            bias=False, dilation=1)
        self.cb3 = conv2DBatchNorm(mid_channels, in_channels, 1, 1, 0)

    def forward(self, x):
        residual = x
        x = self.cb3(self.cbr2(self.cbr1(x)))
        return F.relu(x + residual, inplace=True)

class bottleNeckPSP(nn.Module):
    def __init__(self, in_channels, mid_channels, out_channels,
                 stride, dilation=1):
        super(bottleNeckPSP, self).__init__()

        self.cbr1 = conv2DBatchNormRelu(in_channels, mid_channels, 1, 1, 0, bias=False)
        if dilation > 1:
            self.cbr2 = conv2DBatchNormRelu(mid_channels, mid_channels, 3, 1,
                                            padding=dilation, bias=False,
                                            dilation=dilation)
        else:
            self.cbr2 = conv2DBatchNormRelu(mid_channels, mid_channels, 3,
                                            stride=stride, padding=1,
                                            bias=False, dilation=1)
        self.cb3 = conv2DBatchNorm(mid_channels, out_channels, 1, 1, 0)
        self.cb4 = conv2DBatchNorm(in_channels, out_channels, 1, stride, 0)

    def forward(self, x):
        conv = self.cb3(self.cbr2(self.cbr1(x)))
        residual = self.cb4(x)
        return F.relu(conv + residual, inplace=True)


class residualBlockPSP(nn.Module):
    
    def __init__(self, n_blocks, in_channels, mid_channels, out_channels, stride, dilation=1):
        super(residualBlockPSP, self).__init__()

        if dilation > 1:
            stride = 1

        layers = [bottleNeckPSP(in_channels, mid_channels, out_channels, stride, dilation)]
        for i in range(n_blocks):
            layers.append(bottleNeckIdentifyPSP(out_channels, mid_channels, stride, dilation))

        self.layers = nn.Sequential(*layers)

    def forward(self, x):
        return self.layers(x)

class pyramidPooling(nn.Module):

    def __init__(self, in_channels, pool_sizes):
        super(pyramidPooling, self).__init__()

        self.paths = []
        for i in range(len(pool_sizes)):
            self.paths.append(conv2DBatchNormRelu(in_channels, int(in_channels / len(pool_sizes)), 1, 1, 0, bias=False))

        self.path_module_list = nn.ModuleList(self.paths)
        self.pool_sizes = pool_sizes

    def forward(self, x):
        output_slices = [x]
        h, w = x.view()[2:]

        for module, pool_size in zip(self.path_module_list, self.pool_sizes):
            out = F.avg_pool2d(x, pool_size, 1, 0)
            out = module(out)
            out = F.upsample(out, size=(h,w), mode='bilinear')
            output_slices.append(out)

        return torch.cat(output_slices, dim=1)
